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
### Engine Simulation

An OF ratio of 2.1 is fixed to limit chamber wall temperature. This comes with a penalty of 110 s of Isp compared to the optimal, but reduces the combustion temperature by YYY C, as seen in the plot of combustion temperature vs OF. 

![A:\Projects\Rockets\Liquid\tc_isp_vs_of.png](file:///a%3A/Projects/Rockets/Liquid/tc_isp_vs_of.png)
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
