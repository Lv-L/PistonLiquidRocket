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

| Fuel Type               | Safety   | Cost                                                                                 | Availability          | Flame                        |
| ----------------------- | -------- | ------------------------------------------------------------------------------------ | --------------------- | ---------------------------- |
| Isopropyl alcohol (IPA) | Good     | [$4.5/L](https://www.sydneysolvents.com.au/isopropyl-alcohol-100-20-litre)           | Delivery              | Faint orange                 |
| Ethanol                 | Good     | [$4.0/L](https://www.sydneysolvents.com.au/industrial-methylated-spirits-20-litre)   | Delivery              | Almost invisible blue/yellow |
| Diesel                  | Good     | [$2.1/L](https://petrolspy.com.au/map/latlng/-27.530393745221538/153.04868461871592) | Any petrol station    | Bright orange                |
| E85                     | Moderate | [$2.3/L](https://petrolspy.com.au/map/latlng/-27.544466300664432/153.06961875315346) | United petrol station | Moderate orange/light blue   |
| Acetone                 | Moderate | [$4.8/L](https://www.sydneysolvents.com.au/acetone-20-litre)                         | Delivery              | Moderate orange/blue         |
| Methanol                | Poor     | [$2.5/L](https://www.sydneysolvents.com.au/methanol-20-litre)                        | Delivery              | Almost invisible light blue  |
On the basis of safety, the use of methanol was ruled out due to its high toxicity.

IPA was chosen as the engine's fuel, due to its . An OF ratio of 2.1 is fixed to limit chamber wall temperature. This comes with a penalty of 110 s of Isp compared to the optimal, but reduces the combustion temperature by YYY C, as seen in the plot of combustion temperature vs OF. 
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
