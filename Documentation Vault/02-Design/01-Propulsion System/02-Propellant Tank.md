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
N2O saturation pressure at 35C: 7.03 MPa, 1020 psi

### Tank Burst
Hoop stress:
$\sigma_H=\frac{Pr}{t}$
$\sigma_A=\frac{Pr}{2t}$
$\sigma_{VM}=\sqrt{\sigma_H^2-\sigma_H \sigma_A + \sigma_A^2}$

Where
r = radius (taken as outer radius for maximum)
t = thickness
H: hoop
A: axial
VM: Von Mises

![A:\Projects\Rockets\Liquid\Hoop Stress.png](file:///a%3A/Projects/Rockets/Liquid/Hoop%20Stress.png)

Given that the machining constraints would limit the wall thickness of the tank to > 2mm, and at 3.0 mm machining would not be required, as it is a standard tube thickness. Hence, a tube thickness of 3.0 mm was chosen.

## Bolt Tear-Out

6x M6 bolts:

![A:\Projects\Rockets\Liquid\bolt_tearout.png](file:///a%3A/Projects/Rockets/Liquid/bolt_tearout.png)