# Propellant Tank

## Specifications

| Tank specification type     | Spec       | Justification                                                              |
| --------------------------- | ---------- | -------------------------------------------------------------------------- |
| Volume (fuel + oxidiser)    | 5 L        | From simulation                                                            |
| Outer diameter (stock size) | 100 mm     | Accommodates 4" airframe and standard metric stock size                    |
| Tank material               | Al 6061-T6 | Aluminium for Tripoli rules<br>6061-T6 high strength and good availability |
| Pressurisation              | Piston     | Pressurised by vapor pressure of N2O (Tripoli)                             |
| Passive depressurisation    | Vent hole  | To meet passive depressurisation requirement (Tripoli)                     |
## Sizing

Total tank volume of 5 L split between ox and fuel sections by O/F mass ratio and liquid densities, with a 5% ullage allowance on the ox side (located in the piston cavity).

| Parameter            | Value                              |
| --------------------- | ----------------------------------- |
| N₂O fill density      | 790 kg/m³                          |
| Ullage fraction        | 5%                                  |
| Ox section volume     | 3.381 L (liquid 3.212 L + ullage 169 cm³) |
| Fuel section volume    | 1.619 L                            |
| Ox tube length         | 396.1 mm                           |
| Fuel tube length       | 199.7 mm                           |
| Ox/fuel tube ratio     | 1.983                              |
| Piston ullage cavity   | 35.4 mm deep × 78 mm dia            |

## Structural Calculations

Design pressure: N₂O saturation pressure at 35°C — **P = 7.03 MPa (1020 psi)**
Tank tube: Do = 108.0 mm, Di = 101.6 mm, wall t = 3.2 mm, Al 6061-T6 (σ_Y = 276 MPa)
Safety factor target: SF = 1.5

### Tank Burst

Pressure vessel hoop and axial stresses, combined via Von Mises. Outer radius used as conservative maximum.

$$\sigma_H = \frac{P r}{t}, \qquad \sigma_A = \frac{P r}{2t}, \qquad \sigma_{VM} = \sqrt{\sigma_H^2 - \sigma_H \sigma_A + \sigma_A^2}$$

With $r = D_o/2 = 54.0\ \text{mm}$, $t = 3.2\ \text{mm}$:

$$\sigma_H = \frac{7.03 \times 54.0}{3.2} = 118.6\ \text{MPa}, \qquad \sigma_A = 59.3\ \text{MPa}$$

$$\sigma_{VM} = 102.7\ \text{MPa} \qquad \Rightarrow \qquad SF_{burst} = \frac{276}{102.7} = \mathbf{2.69}$$

### Bolt Retention

The bulkhead is retained by **12× M6 Grade 12.9** radial bolts through the tank wall. Clearance hole Ø6.6 mm, axial edge distance e = 14 mm.

Material properties: $τ_Y = σ_Y/√3 = 159.4 \ MPa$ (wall shear yield), $σ_{br,Y} = 386\  MPa$ (bearing yield, ≈1.4 × $σ_Y$, $σ_{Y,bolt} = 1080 \ MPa$.

Total axial pressure load and load per bolt:

$$F = \frac{\pi}{4} D_i^2 P = \frac{\pi}{4}(101.6)^2 \times 7.03 = 56{,}994\ \text{N}, \qquad F_{bolt} = \frac{F}{N} = \frac{56{,}994}{12} = 4{,}750\ \text{N}$$

#### Tearout

Shear-out of tank wall axially past the bolt hole (two shear planes per bolt):

$$F_{tearout} = \tau_Y \cdot 2t \left(e - \frac{d_h}{2}\right) = 159.4 \times 2(3.2)\left(14 - 3.3\right) = 10{,}912\ \text{N}$$

$$SF_{tearout} = \frac{F_{tearout}}{F_{bolt}} = \frac{10{,}912}{4{,}750} = \mathbf{2.30}$$

Minimum edge distance at SF = 1.5: $e_{min} = d_h/2 + F_{bolt} \cdot SF\,/\,(2t\tau_Y) = 10.29\ \text{mm}$

![[bolt_tearout.png]]

#### Bolt Shear

Single shear across bolt cross-section at the inner wall surface:

$$F_{shear} = \frac{\sigma_{Y,bolt}}{\sqrt{3}} \cdot \frac{\pi}{4} d^2 = 623.5 \times \frac{\pi}{4}(6)^2 = 17{,}630\ \text{N}$$

$$SF_{shear} = \frac{17{,}630}{4{,}750} = \mathbf{3.71}$$

#### Net Section Tensile Failure

Tensile failure of the tank wall between bolt holes. The bolt holes reduce the net cross-sectional area at the failure plane (mean circumference π(Do − t)). Hoop stress from internal pressure acts simultaneously and is combined via Von Mises.

$$\sigma_{axial} = \frac{\frac{\pi}{4} D_i^2 P}{\left[\pi(D_o - t) - N d_h\right] t} = \frac{56{,}994}{\left[\pi(104.8) - 12(6.6)\right] \times 3.2} = 71.2\ \text{MPa}$$

$$\sigma_{hoop} = \frac{P \cdot D_i/2}{t} = \frac{7.03 \times 50.8}{3.2} = 111.6\ \text{MPa}$$

$$\sigma_{VM} = \sqrt{\sigma_{axial}^2 + \sigma_{hoop}^2 - \sigma_{axial}\,\sigma_{hoop}} = 97.9\ \text{MPa}$$

$$SF_{net} = \frac{\sigma_Y}{\sigma_{VM}} = \frac{276}{97.9} = \mathbf{2.82}$$

#### Bearing Failure

Compressive crushing of tank wall material at the bolt hole edge:

$$\sigma_{bearing} = \frac{F_{bolt}}{d \cdot t} = \frac{4{,}750}{6.0 \times 3.2} = 247.4\ \text{MPa}$$

$$SF_{bearing} = \frac{\sigma_{br,Y}}{\sigma_{bearing}} = \frac{386}{247.4} = \mathbf{1.56}$$

#### Summary

| Failure mode | SF   |
| ------------ | ---- |
| Tank burst   | 2.69 |
| Tearout      | 2.30 |
| Bolt shear   | 3.71 |
| Net section  | 2.82 |
| Bearing      | 1.56 |

## Sealing

From [Marco Rubber](https://www.marcorubber.com/o-ring-groove-design-considerations.htm):

Squeeze/compression: 18-25% (male/female static), 10-20% (reciprocating)
Stretch: 0-5%
Gland fill: 75% nominal

Extrusion gap (in inches):
![[O-ring Extrusion.png]]
### Bulkheads
![[O-ring Bulkheads.png]]

### Piston
![[O-ring Piston.png]]

# Interfaces
