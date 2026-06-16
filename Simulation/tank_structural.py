import os
import numpy as np
import matplotlib.pyplot as plt
plt.style.use('ggplot')

PLOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'Documentation Vault', '99-Attachments')

# ── Inputs ─────────────────────────────────────────────────────────────────────
P           = 7.03e6    # Internal pressure, Pa
tank_id     = 95.2e-3   # Tank inner diameter, m
tank_od     = 101.6e-3  # Tank outer diameter, m
n_bolts     = 10        # Number of radial retaining bolts
bolt_d      = 6.0e-3   # Bolt major diameter (bearing, shear), m
hole_d      = 6.6e-3   # Clearance hole diameter (tearout, net section), m
e_actual    = 12.0e-3   # Actual axial edge distance (hole centre to tank end), m
e_min       = 5.0e-3    # Min edge distance for plot, m
e_max       = 20.0e-3   # Max edge distance for plot, m
npoints     = 200

sigmaY        = 276e6   # Yield strength of tank material, Pa  (Al 6061-T6)
sigmaBearingY = 386e6   # Bearing yield of tank material, Pa  (Al 6061-T6, ~1.4 × sigmaY per MIL-HDBK-5)
sigmaY_bolt   = 640e6   # Yield strength of bolt material, Pa  (Grade 8.8 steel)
SF            = 1.5     # Safety factor

# ── Derived ────────────────────────────────────────────────────────────────────
wall_t      = (tank_od - tank_id) / 2                # Tank wall thickness, m
F_applied   = P * np.pi / 4 * tank_id**2             # Total axial load from pressure, N
F_per_bolt  = F_applied / n_bolts                    # Load per bolt, N
F_design    = F_per_bolt * SF                        # Required strength per bolt, N
tauY_wall   = sigmaY      / np.sqrt(3)               # Wall shear yield strength, Pa
tauY_bolt   = sigmaY_bolt / np.sqrt(3)               # Bolt shear yield strength, Pa

# Bolt shear strength (single shear at inner wall surface)
A_bolt       = np.pi / 4 * bolt_d**2
F_bolt_shear = tauY_bolt * A_bolt

# ── Sweep edge distance ────────────────────────────────────────────────────────
es           = np.linspace(e_min, e_max, npoints)
A_tearout    = 2 * wall_t * (es - hole_d / 2)       # Two shear planes per bolt, m^2
F_tearout    = tauY_wall * A_tearout

e_required   = hole_d / 2 + F_design / (2 * wall_t * tauY_wall)

SF_shear_actual   = F_bolt_shear / F_per_bolt
F_tearout_actual  = tauY_wall * 2 * wall_t * (e_actual - hole_d / 2)
SF_tearout_actual = F_tearout_actual / F_per_bolt

# Net section tensile stress in tank wall between bolt holes (Half Cat formula)
# sigma = (pi/4 * Di^2 * P) / [(pi*(Do - wall_t) - N*hole_d) * wall_t]
# pi*(Do - wall_t) is the mean circumference of the wall (failure plane through bolt holes)
sigma_net     = (np.pi / 4 * tank_id**2 * P) / \
                ((np.pi * (tank_od - wall_t) - n_bolts * hole_d) * wall_t)
# Hoop stress also acts at the bolt hole plane — combine via Von Mises
sigma_hoop    = P * (tank_id / 2) / wall_t
sigma_vm_net  = np.sqrt(sigma_net**2 + sigma_hoop**2 - sigma_net * sigma_hoop)
SF_net_actual = sigmaY / sigma_vm_net

# Bearing failure: bolt pushes against edge of hole in tank wall
sigma_bearing     = F_per_bolt / (bolt_d * wall_t)
SF_bearing_actual = sigmaBearingY / sigma_bearing

print(f"Tank wall thickness  : {wall_t*1e3:.1f} mm")
print(f"Load per bolt        : {F_per_bolt:.1f} N")
print(f"Min axial edge dist  : {e_required*1e3:.2f} mm  (tearout, at SF={SF})")
print(f"  (hole d={hole_d*1e3:.1f} mm, wall t={wall_t*1e3:.1f} mm)")
print(f"Actual edge distance : {e_actual*1e3:.1f} mm")
print(f"  Tearout SF         : {SF_tearout_actual:.2f}  ({'OK' if SF_tearout_actual >= SF else 'FAIL'})")
print(f"  Bolt shear SF      : {SF_shear_actual:.2f}  ({'OK' if SF_shear_actual >= SF else 'FAIL'})")
print(f"  Net section SF     : {SF_net_actual:.2f}  ({'OK' if SF_net_actual >= SF else 'FAIL'})  (VM={sigma_vm_net*1e-6:.1f} MPa, axial={sigma_net*1e-6:.1f}, hoop={sigma_hoop*1e-6:.1f})")
print(f"  Bearing SF         : {SF_bearing_actual:.2f}  ({'OK' if SF_bearing_actual >= SF else 'FAIL'})  (sigma={sigma_bearing*1e-6:.1f} MPa)")

# ── Plot ───────────────────────────────────────────────────────────────────────
plt.figure()
plt.title("Radial Bolt Tearout vs Axial Edge Distance")
plt.plot(es * 1e3, F_tearout, label="Wall tearout strength", color='tab:blue', lw=2)
plt.axhline(F_design, color='tab:red', lw=1.5, ls='--',
            label=f"Required (F/bolt x SF{SF} = {F_design:.0f} N)")
if e_min < e_required < e_max:
    plt.axvline(e_required * 1e3, color='gray', lw=1.2, ls=':',
                label=f"Min edge dist = {e_required*1e3:.2f} mm")
plt.xlabel("Axial edge distance, mm  (hole centre to tank end)")
plt.ylabel("Force per bolt, N")
plt.ylim(bottom=0)
plt.legend()
plt.tight_layout()
os.makedirs(PLOT_DIR, exist_ok=True)
plt.savefig(os.path.join(PLOT_DIR, "bolt_tearout.png"), dpi=150, bbox_inches='tight')
plt.show()
