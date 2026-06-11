import numpy as np
import matplotlib.pyplot as plt
plt.style.use('ggplot')

Pmax        = 7.03e6   # Max tank pressure (35C N2O saturation P), Pa
tankOD      = 100.0e-3 # Tank OD, m
tankTmin    = 2.00e-3  # Tank min thickness, m
tankTmax    = 6.00e-3  # Tank max thickness, m
npoints     = 100      # Number of points to calculate
sigmaYield  = 276e6    # Yield strength, Pa
SF          = 1.5      # Safety factor

sigmaDesign = sigmaYield/SF

### INITIALISE ARRAYS
ts          = np.linspace(tankTmin,tankTmax,npoints)
rs          = tankOD/2

### HOOP STRESS
sigmarHoop  = Pmax*rs/ts
sigmaaHoop  = Pmax*rs/(2*ts)
sigmavmHoop = np.sqrt(sigmarHoop**2-sigmarHoop*sigmaaHoop+sigmaaHoop**2)

plt.title("Stress vs Wall Thickness")
plt.plot(ts*1e3,sigmavmHoop*1e-6,label="Von Mises stress")
plt.plot(np.array([tankTmin,tankTmax])*1.0e3,
         np.array([sigmaDesign,sigmaDesign])*1e-6,
         label=f"Design stress = {sigmaDesign*1e-6} MPa")
plt.ylabel("Stress, MPa")
plt.xlabel("Wall Thickness, mm")
plt.ylim([0,None])
plt.legend()
plt.savefig("Hoop Stress.png", dpi=150, bbox_inches='tight')
plt.show()

