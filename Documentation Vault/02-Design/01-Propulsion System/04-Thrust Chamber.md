# Injector
The injector used is a simple scrintle injector. This sprays the central oxidiser flow axially onto the underside of a bolt head, which redirects it radially to impinge on the axial fuel flow from holes at a larger diameter. A steel spacer is used between the injector face and screw head.

Screw: https://www.amazon.com.au/uxcell-M6x20mm-Slotted-Screws-Stainless/dp/B0CWL8S9KT

For injector sizing, areas were calculated to target a chamber pressure 50% of the feed pressure at the beginning of the burn. At the end of the burn, this moves to about 58%.

This gives an injector area of:
- 18.55 mm2 for the oxidiser injector
- 9.89 mm2 for the fuel injector

Assuming a discharge coefficient of 0.6 for the injector orifices, and taking into account pressure losses along the feed lines using the Darcy-Weisbach equation, with a roughness of 1.5e-6.
# Structural Calculations

# Sealing

## Injector/Combustion Chamber

![[O-ring Injector.png]]

## Combustion Chamber/Nozzle

### Nozzle
A nozzle throat diameter of 25 mm was chosen in the concepting stage of the engine.

The nozzle uses a copper insert for the throat, press fit into the aluminium nozzle. This fit will loosen during operation due to the coefficient of thermal expansion (CTE) of aluminium being higher than copper, but it will be sufficient to ensure the insert doesn't move during handling.
![[Nozzle.png]]

### Sealing
Using Half Cat's concept of a graphite flange seal, [KLINGER's PSM graphite laminate](https://www.klinger.com.au/products/jointing-gasket-materials/graphite-laminates/klinger-graphite-laminate-psm/) was chosen for being rated to high temperatures (450 C) and sufficient pressure for the chamber (rated to 80 bar).

Calculation for required torqueing of bolts for sufficient gasket compression:

$F_{clamp}=P_{gasket} A_{gasket}+P_{chamber} A_{chamber}$
$F_{clamp}=30\ MPa \cdot 386.4\ mm^2 + 3\ MPa \cdot 2827\ mm^2=20073\ N$

For an M6 bolt, effective area = $20.1\ mm^2$
For low-tensile grade 4.6, yield strength = $240 \ MPa$ 
Use 8 bolts

$SF_{yield}=(\sigma_y \cdot A_{eff} \cdot N_{bolts}/F_{clamp})$
$SF_{yield}=(240\cdot 20.1\cdot8)/20073=1.92$

Preload torque required:
$T=K_T\cdot D_{bolt} \cdot F_{clamp}/N_{bolts}$

$K_T$ (nut factor) typically = 0.2 for unlubricated threads

$T=0.2\cdot 0.006 \ m \cdot 20073 \ N/8=3.01 \ Nm$

[M6 zinc coated threaded rod](https://www.boltandnut.com.au/m6-x-1-00p-x-1-metre-1000mm-metric-coarse-zinc-low-tensile-allthread-threaded-rod-din-975) Will be used for the clamping threads.
