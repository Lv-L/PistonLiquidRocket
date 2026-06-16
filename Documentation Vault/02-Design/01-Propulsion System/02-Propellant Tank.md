# Propellant Tank

## Specifications

| Tank specification type     | Spec       | Justification                                                              |
| --------------------------- | ---------- | -------------------------------------------------------------------------- |
| Volume (fuel + oxidiser)    | 5 L        | From simulation                                                            |
| Outer diameter (stock size) | 100 mm     | Accommodates 4" airframe and standard metric stock size                    |
| Tank material               | Al 6061-T6 | Aluminium for Tripoli rules<br>6061-T6 high strength and good availability |
| Pressurisation              | Piston     | Pressurised by vapor pressure of N2O (Tripoli)                             |
| Passive depressurisation    | Vent hole  | To meet passive depressurisation requirement (Tripoli)                     |
## Structural Calculations

Design pressure: N₂O saturation pressure at 35°C — **P = 7.03 MPa (1020 psi)**
Tank tube: Do = 101.6 mm, Di = 95.2 mm, wall t = 3.2 mm, Al 6061-T6 (σ_Y = 276 MPa)
Safety factor target: SF = 1.5

### Tank Burst

Pressure vessel hoop and axial stresses, combined via Von Mises. Outer radius used as conservative maximum.

$$\sigma_H = \frac{P r}{t}, \qquad \sigma_A = \frac{P r}{2t}, \qquad \sigma_{VM} = \sqrt{\sigma_H^2 - \sigma_H \sigma_A + \sigma_A^2}$$

With $r = D_o/2 = 50.8\ \text{mm}$, $t = 3.2\ \text{mm}$:

$$\sigma_H = \frac{7.03 \times 50.8}{3.2} = 111.6\ \text{MPa}, \qquad \sigma_A = 55.8\ \text{MPa}$$

$$\sigma_{VM} = 96.7\ \text{MPa} \qquad \Rightarrow \qquad SF_{burst} = \frac{276}{96.7} = \mathbf{2.86 \ ✓}$$

A 101.6 mm OD × 3.2 mm wall tube is standard 4" aluminium stock — no machining required.

![[Hoop Stress.png]]

### Bolt Retention

The bulkhead is retained by **10× M6 Grade 8.8** radial bolts through the tank wall. Clearance hole Ø6.6 mm, axial edge distance e = 12 mm.

Material properties: τ_Y = σ_Y/√3 = 159.4 MPa (wall shear yield), σ_{br,Y} = 386 MPa (bearing yield, ≈1.4 × σ_Y per MIL-HDBK-5), σ_{Y,bolt} = 640 MPa.

Total axial pressure load and load per bolt:

$$F = \frac{\pi}{4} D_i^2 P = \frac{\pi}{4}(95.2)^2 \times 7.03 = 50{,}040\ \text{N}, \qquad F_{bolt} = \frac{F}{N} = \frac{50{,}040}{10} = 5{,}004\ \text{N}$$

#### Tearout

Shear-out of tank wall axially past the bolt hole (two shear planes per bolt):

$$F_{tearout} = \tau_Y \cdot 2t \left(e - \frac{d_h}{2}\right) = 159.4 \times 2(3.2)\left(12 - 3.3\right) = 8{,}862\ \text{N}$$

$$SF_{tearout} = \frac{F_{tearout}}{F_{bolt}} = \frac{8{,}862}{5{,}004} = \mathbf{1.77 \ ✓}$$

Minimum edge distance at SF = 1.5: $e_{min} = d_h/2 + F_{bolt} \cdot SF\,/\,(2t\tau_Y) = 10.7\ \text{mm}$

![[bolt_tearout.png]]

#### Bolt Shear

Single shear across bolt cross-section at the inner wall surface:

$$F_{shear} = \frac{\sigma_{Y,bolt}}{\sqrt{3}} \cdot \frac{\pi}{4} d^2 = 369.5 \times \frac{\pi}{4}(6)^2 = 10{,}453\ \text{N}$$

$$SF_{shear} = \frac{10{,}453}{5{,}004} = \mathbf{2.09 \ ✓}$$

#### Net Section Tensile Failure

Tensile failure of the tank wall between bolt holes. The bolt holes reduce the net cross-sectional area at the failure plane (mean circumference π(Do − t)). Hoop stress from internal pressure acts simultaneously and is combined via Von Mises.

$$\sigma_{axial} = \frac{\frac{\pi}{4} D_i^2 P}{\left[\pi(D_o - t) - N d_h\right] t} = \frac{50{,}040}{\left[\pi(98.4) - 10(6.6)\right] \times 3.2} = 64.3\ \text{MPa}$$

$$\sigma_{hoop} = \frac{P \cdot D_i/2}{t} = \frac{7.03 \times 47.6}{3.2} = 104.6\ \text{MPa}$$

$$\sigma_{VM} = \sqrt{\sigma_{axial}^2 + \sigma_{hoop}^2 - \sigma_{axial}\,\sigma_{hoop}} = 91.4\ \text{MPa}$$

$$SF_{net} = \frac{\sigma_Y}{\sigma_{VM}} = \frac{276}{91.4} = \mathbf{3.02 \ ✓}$$

#### Bearing Failure

Compressive crushing of tank wall material at the bolt hole edge:

$$\sigma_{bearing} = \frac{F_{bolt}}{d \cdot t} = \frac{5{,}004}{6.0 \times 3.2} = 260.6\ \text{MPa}$$

$$SF_{bearing} = \frac{\sigma_{br,Y}}{\sigma_{bearing}} = \frac{386}{260.6} = \mathbf{1.48}$$

Bearing is the critical failure mode (SF = 1.48 < 1.5 target). This is accepted on the same basis as Half Cat: N₂O saturation physics prevent tank pressure from reaching 7.03 MPa unless the tank exceeds 35°C, which is not possible under normal launch conditions. Actual operating pressure is substantially lower.

#### Summary

| Failure mode   | SF    | Status        |
| -------------- | ----- | ------------- |
| Tank burst     | 2.86  | ✓             |
| Tearout        | 1.77  | ✓             |
| Bolt shear     | 2.09  | ✓             |
| Net section    | 3.02  | ✓             |
| Bearing        | 1.48  | Acceptable\*  |

\* Bearing SF < 1.5 accepted: design pressure is a physical maximum, not a worst-case estimate.