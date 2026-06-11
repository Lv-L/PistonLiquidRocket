import numpy as np
import matplotlib.pyplot as plt
plt.style.use('ggplot')

# ── Inputs ─────────────────────────────────────────────────────────────────────
P           = 7.03e6    # Internal pressure, Pa
tank_id     = 94.0e-3   # Tank inner diameter, m
n_bolts     = 6         # Number of bolts sharing the load
bolt_d      = 6.0e-3    # Bolt / hole diameter, m
t           = 4.0e-3    # Plate thickness, m
e_min       = 5.0e-3    # Min edge distance (hole centre to edge), m
e_max       = 16.0e-3   # Max edge distance, m
npoints     = 200

sigmaY      = 276e6     # Yield strength of plate material, Pa  (Al 6061-T6)
sigmaY_bolt = 640e6     # Yield strength of bolt material, Pa   (Grade 8.8 steel)
SF          = 1.3       # Safety factor

# ── Derived ────────────────────────────────────────────────────────────────────
F_applied   = P * np.pi * (tank_id / 2)**2 # Total axial load from pressure, N
F_per_bolt  = F_applied / n_bolts          # Load per bolt, N
F_design    = F_per_bolt * SF              # Required strength per bolt, N
tauY_plate  = sigmaY      / np.sqrt(3)     # Plate shear yield strength, Pa
tauY_bolt   = sigmaY_bolt / np.sqrt(3)     # Bolt  shear yield strength, Pa

# Bolt shear strength (single shear — one shear plane across bolt cross-section)
A_bolt      = np.pi * (bolt_d / 2) ** 2   # Bolt cross-section area, m^2
F_bolt_shear = tauY_bolt * A_bolt          # Bolt shear strength, N

# ── Sweep edge distance ────────────────────────────────────────────────────────
es           = np.linspace(e_min, e_max, npoints)
A_tearout    = 2 * t * (es - bolt_d / 2)  # Shear-out area (two shear planes), m^2
F_tearout    = tauY_plate * A_tearout      # Plate tearout strength, N

# Minimum edge distance for tearout to meet design load
e_required = bolt_d / 2 + F_design / (2 * t * tauY_plate)

SF_shear_actual = F_bolt_shear / F_per_bolt

print(f"Load per bolt        : {F_per_bolt:.1f} N")
print(f"Min edge distance    : {e_required*1e3:.2f} mm  (tearout, at SF={SF})")
print(f"  (hole centre to edge, bolt d={bolt_d*1e3:.1f} mm, t={t*1e3:.1f} mm)")
print(f"Bolt shear SF        : {SF_shear_actual:.2f}  ({'OK' if SF_shear_actual >= SF else 'FAIL'})")

# ── Plot ───────────────────────────────────────────────────────────────────────
plt.figure()
plt.title("Bolt Joint Strength vs Edge Distance")
plt.plot(es * 1e3, F_tearout, label="Plate tearout strength", color='tab:blue', lw=2)
plt.axhline(F_bolt_shear, color='tab:orange', lw=2,
            label=f"Bolt shear strength = {F_bolt_shear:.0f} N  (SF={SF_shear_actual:.2f})")
plt.axhline(F_design, color='tab:red', lw=1.5, ls='--',
            label=f"Required (F/bolt × SF{SF} = {F_design:.0f} N)")
if e_min < e_required < e_max:
    plt.axvline(e_required * 1e3, color='gray', lw=1.2, ls=':',
                label=f"Min edge dist = {e_required*1e3:.2f} mm")
plt.xlabel("Edge distance, mm  (hole centre to plate edge)")
plt.ylabel("Force per bolt, N")
plt.ylim(bottom=0)
plt.legend()
plt.tight_layout()
plt.savefig("bolt_tearout.png", dpi=150, bbox_inches='tight')
plt.show()
