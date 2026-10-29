// GSE vehicle controller — ESP32 Dev Module / NodeMCU-32S.
// Bluetooth name: GSE-VEHICLE. The Pi connects with classic Bluetooth RFCOMM.
// The same command lines also work on USB serial for a bench checkout.
// There is no electrical link to the pad in operation. Power is the vehicle
// 5 V UBEC into the ESP32 5 V pin. Do not power the servos from the 3.3 V pin.
//
// Signal wiring. Common the UBEC ground and the ESP32 ground.
//   GPIO 25  ox main DS3225 signal
//   GPIO 26  fuel main DS3225 signal
//
// DS3225 is a 180 degree servo. Main-run ball valves are quarter-turn.
// Default travel is about 90 degrees (1000 us closed, 2000 us open).
// Edit CLOSE_US / OPEN_US once the horn is on the valve.
//
// Board package: ESP32 by Espressif, "ESP32 Dev Module" or "NodeMCU-32S".
// The 3.3 V PWM high is normally enough for a DS3225 signal pin. If a servo
// jitters, buffer the signal; do not feed the ESP32 a 5 V signal back into the pin.

#include "BluetoothSerial.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Enable classic Bluetooth in the ESP32 board tools menu
#endif

static const int PIN_OX = 25;
static const int PIN_FUEL = 26;
static const int CH_OX = 0;
static const int CH_FUEL = 1;

static const int CLOSE_US = 1000;
static const int OPEN_US = 2000;
static const int SERVO_HZ = 50;
static const int SERVO_BITS = 16;

static const unsigned long WATCHDOG_MS = 4000;

bool armed = false;
bool oxOpen = false;
bool fuelOpen = false;
unsigned long lastCommandMs = 0;

struct Reader {
  Stream *io;
  char line[64];
  uint8_t len;
  bool overflow;
};

BluetoothSerial SerialBT;
Reader usbReader;
Reader btReader;

uint32_t usToDuty(int us) {
  if (us < 500) us = 500;
  if (us > 2500) us = 2500;
  return (uint32_t)us * ((1UL << SERVO_BITS) - 1) / 20000UL;
}

void writeServo(int pin, int channel, int us) {
#if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
  (void)channel;
  ledcWrite(pin, usToDuty(us));
#else
  ledcWrite(channel, usToDuty(us));
#endif
}

void attachServo(int pin, int channel) {
#if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
  (void)channel;
  ledcAttach(pin, SERVO_HZ, SERVO_BITS);
#else
  ledcSetup(channel, SERVO_HZ, SERVO_BITS);
  ledcAttachPin(pin, channel);
#endif
  writeServo(pin, channel, CLOSE_US);
}

void setOx(bool openValve) {
  oxOpen = openValve;
  writeServo(PIN_OX, CH_OX, openValve ? OPEN_US : CLOSE_US);
}

void setFuel(bool openValve) {
  fuelOpen = openValve;
  writeServo(PIN_FUEL, CH_FUEL, openValve ? OPEN_US : CLOSE_US);
}

void safeAll() {
  armed = false;
  setOx(false);
  setFuel(false);
}

void reply(Stream &io, const char *msg) {
  io.println(msg);
}

void replyStatus(Stream &io) {
  io.print("STATUS vehicle armed=");
  io.print(armed ? "1" : "0");
  io.print(" ox=");
  io.print(oxOpen ? "OPEN" : "CLOSED");
  io.print(" fuel=");
  io.println(fuelOpen ? "OPEN" : "CLOSED");
}

bool requireArm(Stream &io) {
  if (armed) {
    return true;
  }
  reply(io, "ERR DISARMED");
  return false;
}

void handle(Stream &io, char *cmd) {
  lastCommandMs = millis();
  if (strcmp(cmd, "PING") == 0) {
    reply(io, "OK PONG");
    return;
  }
  if (strcmp(cmd, "SAFE") == 0) {
    safeAll();
    reply(io, "OK SAFE");
    return;
  }
  if (strcmp(cmd, "ARM") == 0) {
    armed = true;
    reply(io, "OK ARM");
    return;
  }
  if (strcmp(cmd, "STATUS") == 0) {
    replyStatus(io);
    return;
  }
  if (strcmp(cmd, "OX OPEN") == 0) {
    if (!requireArm(io)) return;
    setOx(true);
    reply(io, "OK OX OPEN");
    return;
  }
  if (strcmp(cmd, "OX CLOSE") == 0) {
    setOx(false);
    reply(io, "OK OX CLOSE");
    return;
  }
  if (strcmp(cmd, "FUEL OPEN") == 0) {
    if (!requireArm(io)) return;
    setFuel(true);
    reply(io, "OK FUEL OPEN");
    return;
  }
  if (strcmp(cmd, "FUEL CLOSE") == 0) {
    setFuel(false);
    reply(io, "OK FUEL CLOSE");
    return;
  }
  reply(io, "ERR UNKNOWN");
}

void poll(Reader &reader) {
  while (reader.io->available() > 0) {
    char c = (char)reader.io->read();
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      reader.line[reader.len] = '\0';
      if (!reader.overflow && reader.len > 0) {
        handle(*reader.io, reader.line);
      } else if (reader.overflow) {
        reply(*reader.io, "ERR LINE");
      }
      reader.len = 0;
      reader.overflow = false;
      continue;
    }
    if (c >= 'a' && c <= 'z') {
      c = c - 'a' + 'A';
    }
    if (reader.len < sizeof(reader.line) - 1) {
      reader.line[reader.len++] = c;
    } else {
      reader.overflow = true;
    }
  }
}

void setup() {
  Serial.begin(115200);
  attachServo(PIN_OX, CH_OX);
  attachServo(PIN_FUEL, CH_FUEL);
  safeAll();
  SerialBT.begin("GSE-VEHICLE");
  usbReader.io = &Serial;
  btReader.io = &SerialBT;
  lastCommandMs = millis();
}

void loop() {
  poll(usbReader);
  poll(btReader);
  if (armed && (millis() - lastCommandMs) > WATCHDOG_MS) {
    safeAll();
  }
}
