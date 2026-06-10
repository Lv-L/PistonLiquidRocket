# Propulsion System Overview

## Propellant Selection
<!-- Oxidizer / fuel choices, reasoning -->

## Performance Targets
| Parameter       | Value       |
| --------------- | ----------- |
| Total impulse   | 5000 Ns     |
| Liftoff TWR     | 5 (minimum) |
| Pressure rating | 1000 psi    |
Total impulse: 5000 Ns to stay under L2 limit of 5120 Ns [(L motor)](https://en.wikipedia.org/wiki/Model_rocket_motor_classification)
TWR: "at least" 5, from [Tripoli](https://www.tripoli.org/safetycode) - **880 N minimum initial thrust** at an initial mass estimate of 18 kg (from Half Cat, full propellant load)
Pressure rating: 1000 psi for saturation pressure of N2O at 35 deg C
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
| Ethanol                 | Good     | [$4.0/L](https://www.sydneysolvents.com.au/industrial-methylated-spirits-20-litre)   | Delivery              | 260 s       | Almost invisible blue/yellow | Sometimes low purity            |
| Diesel                  | Good     | [$2.1/L](https://petrolspy.com.au/map/latlng/-27.530393745221538/153.04868461871592) | Any petrol station    | 251 s       | Bright orange                | Leaves oily film                |
| E85                     | Moderate | [$2.3/L](https://petrolspy.com.au/map/latlng/-27.544466300664432/153.06961875315346) | United petrol station | 258 s       | Moderate orange/light blue   | More flammable than ethanol     |
| Acetone                 | Moderate | [$4.8/L](https://www.sydneysolvents.com.au/acetone-20-litre)                         | Delivery              | 253 s       | Moderate orange/blue         | Tends to swell O-rings          |
| Methanol                | Poor     | [$2.5/L](https://www.sydneysolvents.com.au/methanol-20-litre)                        | Delivery              | ~           | Almost invisible light blue  | "Should not be used" - Half Cat |
On the basis of safety, the use of methanol was ruled out due to its high toxicity.

For propellants, ethanol and E85 were chosen. Ethanol for its performance and lack of residue, and E85 for "show", with it having a more visible orange flame. Given that E85 has lower performance, the ethanol case will be used to establish a conservative "upper limit" of performance.

![A:\Projects\Rockets\Liquid\Simulation\tc_isp_vs_lambda.png](file:///a%3A/Projects/Rockets/Liquid/Simulation/tc_isp_vs_lambda.png)

An OF of 2 will be used initially to reduce flame temperature with a small penalty in Isp. For ethanol, an OF ratio of 2 results in an adiabatic flame temperature of 2828 K and an Isp of 252 s. This means a penalty of 8 s of Isp gives a temperature reduction of 489 K (with ethanol's peak Isp being 260 s at an adiabatic flame temperature of 3317 K).

### Nozzle
The nozzle throat diameter and expansion ratio were copied from Half Cat:

| Variable             | Value |
| -------------------- | ----- |
| Throat diameter (mm) | 25.4  |
| Expansion Ratio      | 4     |

### Combustion Chamber
Chamber dimensions were copied from Half Cat, given that chamber sizing is typically done from past experience.

| **Dimension name**         | Dimension (mm) |
| -------------------------- | -------------- |
| Chamber ID                 | 51             |
| Chamber length             | 127            |
| Characteristic length (L*) | 635            |
### Components
#### Tanks
The tank is a "piston style" tank that is the same as Half Cat's design, where the vapor pressure of the N2O pushes along a piston to expel the fuel. From the Half Cat Mojave Sphinx Guidebook:
![[Pasted image 20260610212356.png]]
#### Regulators
No regulators are used - instead the main valves are set to open at a point between the operating pressure and the burst pressure of the tank, in the case of an extremely hot day or radiative heating of the tank resulting in it being heated to greater than 35 degrees C.
#### Valves
1/4" BSP 304 stainless full port ball valve, 1000 psi - [Pacific Fittings](https://www.camlockfittings.com.au/2-piece-ball-valves-ss304.html)
Use 3d print with [DS3225 servo - Amazon](https://www.amazon.com.au/AKLOSIPY-DS3225MG-Digital-Servo-Multiple/dp/B0FX16CGW4?source=ps-sl-shoppingads-lpcontext&psc=1&smid=A1VAS17HV99LTB) to convert to servo valve for ox fill valve, main ox valve and main fuel valve.
#### Plumbing
As shown in [[#Fluid System Architecture]], there is plumbing required for oxidiser and fuel lines. Half Cat's use of braided PTFE flex lines is adopted, along with their sizes of AN6 (7/16" OD) line for the oxidiser and AN5 (3/8" OD) line for the fuel.

## Analysis
The simulation models a piston-fed N2O + liquid fuel rocket where a two-phase N2O tank self-pressurises and drives a piston to expel fuel. At each timestep it computes propellant mass flow rates through injector orifices (using incompressible orifice flow), calls rocketCEA to get ideal combustion properties (T0, γ, MW, c*), applies combustion efficiency to get actual c*, then solves the chamber pressure from c* = Pc·At/ṁ. Thrust and Isp follow from the nozzle expansion, and the N2O tank state evolves via an adiabatic energy balance accounting for liquid/vapour phase change.

For the purposes of initial analysis, a target injector pressure drop was set at 20% initial feed pressure. A combustion efficiency of 65% and a nozzle efficiency of 97% was used. Half Cat's feed line geometries were used to estimate feed line pressure drop, this can be fine tuned as the design progresses to CAD.

Inputs (non exhaustive):
- Tank volume (ox + fuel): 5L
- Ox tank diameter: 95.2 mm
- Ox ullage: 5% by volume
- Fuel: Ethanol
- O/F: 2.0
- Throat diameter: 25.4 mm
- Nozzle expansion ratio: 4

Hot day (30C):
![[engine_simulation_30C.png]]
Results:
- Burn time: 1.970 s
- Average / peak thrust: 2300.7 N / 3247.2 N
- Average Isp: 147.15 s
- Total impulse : 4511.8 N*s
- Average c*: 1023.3 m/s
- N2O temp drop: 30.11 K  (29.5 C -> -0.6 C)
- N2O pressure drop: 6.308 -> 3.078 MPa

Cold day (10C):
![[engine_simulation_10C 1.png]]
Results:
- Burn time: 3.200 s
- Average / peak thrust: 1587.0 N / 2114.8 N
- Average Isp: 142.38 s
- Total impulse: 5067.6 N*s
- Average c*: 1022.4 m/s
- N2O temp drop:  24.33 K  (9.9 C -> -14.4 C)
- N2O pressure drop: 4.001 -> 2.114 MPa
## Related
- [[02-Design/03-Ground Support Equipment/GSE Overview]]
- [[02-Design/04-Flight Systems/Flight Systems Overview]]
