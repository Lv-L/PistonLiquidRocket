// GSE pad controller — Arduino Uno.
// USB to the Raspberry Pi 3B. The Pi is the only thing that should arm this board.
//
// Signal wiring. Servo power comes from the pad 5 V UBEC, not the Uno 5 V pin.
// Common the UBEC ground, the Uno ground, and the relay ground.
//   D9   fill DS3225 signal
//   D10  purge DS3225 signal
//   D4   ignitor relay IN
//   USB  Pi 3B
//
// RELAY_ON_IS_HIGH matches a relay that actuates on a high output.
// A lot of KY-019 modules are active-low. If the relay clicks at boot,
// set RELAY_ON_IS_HIGH to false.
//
// DS3225 is a 180 degree servo. These ball valves are quarter-turn, so the
// default travel is about 90 degrees (1000 us closed, 2000 us open).
// Edit CLOSE_US / OPEN_US once the horn is on the valve. Swap them if it
// turns the wrong way. Do not command a full 180 degrees into a quarter-turn valve.

#include <Servo.h>

static const int PIN_FILL = 9;
static const int PIN_PURGE = 10;
static const int PIN_RELAY = 4;
static const int PIN_LED = 13;
static const bool RELAY_ON_IS_HIGH = true;

static const int CLOSE_US = 1000;
static const int OPEN_US = 2000;

// Pi polls STATUS about once a second. Go safe if those polls stop.
static const unsigned long WATCHDOG_MS = 4000;

Servo fillServo;
Servo purgeServo;

bool armed = false;
bool fillOpen = false;
bool purgeOpen = false;
bool relayOn = false;
unsigned long lastCommandMs = 0;

char line[64];
uint8_t lineLen = 0;
bool overflow = false;

void setRelay(bool on) {
  relayOn = on;
  bool high = RELAY_ON_IS_HIGH ? on : !on;
  digitalWrite(PIN_RELAY, high ? HIGH : LOW);
}

void updateLed() {
  // The Uno's L LED follows the pad valves, so a servo can be ruled out
  // without a second tool. Solid means fill is open. Blinking means purge is open.
  if (fillOpen) {
    digitalWrite(PIN_LED, HIGH);
    return;
  }
  if (purgeOpen) {
    digitalWrite(PIN_LED, (millis() / 200) & 1 ? HIGH : LOW);
    return;
  }
  digitalWrite(PIN_LED, LOW);
}

void setFill(bool openValve) {
  fillOpen = openValve;
  fillServo.writeMicroseconds(openValve ? OPEN_US : CLOSE_US);
  updateLed();
}

void setPurge(bool openValve) {
  purgeOpen = openValve;
  purgeServo.writeMicroseconds(openValve ? OPEN_US : CLOSE_US);
  updateLed();
}

void safeAll() {
  armed = false;
  setRelay(false);
  setFill(false);
  setPurge(false);
}

void reply(const char *msg) {
  Serial.println(msg);
}

void replyStatus() {
  Serial.print("STATUS pad armed=");
  Serial.print(armed ? "1" : "0");
  Serial.print(" relay=");
  Serial.print(relayOn ? "1" : "0");
  Serial.print(" fill=");
  Serial.print(fillOpen ? "OPEN" : "CLOSED");
  Serial.print(" purge=");
  Serial.println(purgeOpen ? "OPEN" : "CLOSED");
}

bool requireArm() {
  if (armed) {
    return true;
  }
  reply("ERR DISARMED");
  return false;
}

void handle(char *cmd) {
  lastCommandMs = millis();
  if (strcmp(cmd, "PING") == 0) {
    reply("OK PONG");
    return;
  }
  if (strcmp(cmd, "SAFE") == 0) {
    safeAll();
    reply("OK SAFE");
    return;
  }
  if (strcmp(cmd, "ARM") == 0) {
    armed = true;
    reply("OK ARM");
    return;
  }
  if (strcmp(cmd, "STATUS") == 0) {
    replyStatus();
    return;
  }
  if (strcmp(cmd, "FILL OPEN") == 0) {
    if (!requireArm()) return;
    setFill(true);
    reply("OK FILL OPEN");
    return;
  }
  if (strcmp(cmd, "FILL CLOSE") == 0) {
    setFill(false);
    reply("OK FILL CLOSE");
    return;
  }
  if (strcmp(cmd, "PURGE OPEN") == 0) {
    if (!requireArm()) return;
    setPurge(true);
    reply("OK PURGE OPEN");
    return;
  }
  if (strcmp(cmd, "PURGE CLOSE") == 0) {
    setPurge(false);
    reply("OK PURGE CLOSE");
    return;
  }
  if (strcmp(cmd, "RELAY ON") == 0) {
    if (!requireArm()) return;
    setRelay(true);
    reply("OK RELAY ON");
    return;
  }
  if (strcmp(cmd, "RELAY OFF") == 0) {
    setRelay(false);
    reply("OK RELAY OFF");
    return;
  }
  reply("ERR UNKNOWN");
}

void setup() {
  pinMode(PIN_RELAY, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_RELAY, RELAY_ON_IS_HIGH ? LOW : HIGH);
  digitalWrite(PIN_LED, LOW);
  fillServo.attach(PIN_FILL);
  purgeServo.attach(PIN_PURGE);
  safeAll();
  Serial.begin(115200);
  lastCommandMs = millis();
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      line[lineLen] = '\0';
      if (!overflow && lineLen > 0) {
        handle(line);
      } else if (overflow) {
        reply("ERR LINE");
      }
      lineLen = 0;
      overflow = false;
      continue;
    }
    if (c >= 'a' && c <= 'z') {
      c = c - 'a' + 'A';
    }
    if (lineLen < sizeof(line) - 1) {
      line[lineLen++] = c;
    } else {
      overflow = true;
    }
  }

  updateLed();

  if (armed && (millis() - lastCommandMs) > WATCHDOG_MS) {
    safeAll();
  }
}
