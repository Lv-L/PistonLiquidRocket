# Propulsion System Overview

## Propellant Selection
<!-- Oxidizer / fuel choices, reasoning -->

## Performance Targets
| Parameter     | Value       |
| ------------- | ----------- |
| Total impulse | 5000 Ns     |
| Liftoff TWR   | 5 (minimum) |
Total impulse: 5000 Ns to stay under L2 limit of 5120 Ns [(L motor)](https://en.wikipedia.org/wiki/Model_rocket_motor_classification)
TWR: "at least" 5, from [Tripoli](https://www.tripoli.org/safetycode) - **880 N minimum initial thrust** at an initial mass estimate of 18 kg (from Half Cat, full propellant load)
## Fluid System Architecture
Pressure fed by nitrous oxide, as required by [Tripoli](https://tripoli.org/content.aspx?page_id=5&club_id=795696&item_id=126571&)

P&ID Diagram:
![[P&ID.png]]

## Engine Architecture
### Oxidiser
Nitrous oxide (N<sub>2</sub>O) is used as the oxidiser due to its explicit requirement by Tripoli. It self-pressurises at room temperature and has limited chemical incompatibilities (unlike liquid oxygen), and is relatively non-toxic (compared to hydrogen peroxide).
### Fuel
A comparison of potential fuel types is summarised below:

| Fuel Type               | Safety   | Cost                                                                                 | Availability          | Max Isp (s) | Flame                        | Notes                           |
| ----------------------- | -------- | ------------------------------------------------------------------------------------ | --------------------- | ----------- | ---------------------------- | ------------------------------- |
| Isopropyl alcohol (IPA) | Good     | [$4.5/L](https://www.sydneysolvents.com.au/isopropyl-alcohol-100-20-litre)           | Delivery              | 257 s       | Faint orange                 | Easy to obtain pure             |
| Ethanol                 | Good     | [$4.0/L](https://www.sydneysolvents.com.au/industrial-methylated-spirits-20-litre)   | Delivery              | 260 s       | Almost invisible blue/yellow | Need to keep an eye on purity   |
| Diesel                  | Good     | [$2.1/L](https://petrolspy.com.au/map/latlng/-27.530393745221538/153.04868461871592) | Any petrol station    | 251 s       | Bright orange                | Leaves oily film                |
| E85                     | Moderate | [$2.3/L](https://petrolspy.com.au/map/latlng/-27.544466300664432/153.06961875315346) | United petrol station | 258 s       | Moderate orange/light blue   | More flammable than ethanol     |
| Acetone                 | Moderate | [$4.8/L](https://www.sydneysolvents.com.au/acetone-20-litre)                         | Delivery              | 253 s       | Moderate orange/blue         | Tends to swell O-rings          |
| Methanol                | Poor     | [$2.5/L](https://www.sydneysolvents.com.au/methanol-20-litre)                        | Delivery              | ~           | Almost invisible light blue  | "Should not be used" - Half Cat |
On the basis of safety, the use of methanol was ruled out due to its high toxicity.

For propellants, ethanol and E85 were chosen. Ethanol for its performance, and E85 for "show", with it having a more visible orange flame. Given that E85 has lower performance, the ethanol case will be used to establish a conservative "upper limit" of performance.

![A:\Projects\Rockets\Liquid\Simulation\tc_isp_vs_lambda.png](file:///a%3A/Projects/Rockets/Liquid/Simulation/tc_isp_vs_lambda.png)
### Combustion Chamber

### Nozzle

### Components
- Tanks
- Regulators
- Valves
- Plumbing

## Analysis
<!-- CEA outputs, thrust calculations, trade studies, P&ID, flow calculations, pressure drop analysis -->

## Related
- [[02-Design/03-Ground Support Equipment/GSE Overview]]
- [[02-Design/04-Flight Systems/Flight Systems Overview]]
