"""
Combustion temperature and Isp vs O/F ratio — N2O oxidiser.
Edit the config block below to change fuels and sweep parameters.

Supported fuels
  IPA      -- Isopropyl alcohol        (C3H8O)
  Ethanol  -- Ethanol                  (C2H6O)
  Methanol -- Methanol                 (CH4O)
  E85      -- 85% ethanol / 15% iso-octane blend

"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PistonLiquidRocket import FUELS, combustion_props, thrust_coefficient, G0, PLOT_DIR

plt.style.use('ggplot')

# ── Configuration ──────────────────────────────────────────────────────────────
SELECTED_FUELS = ['IPA','Ethanol']  # subset of FUELS, or None for all
OF_MIN      = 1.0       # O/F sweep start
OF_MAX      = 8.0       # O/F sweep end
OF_N        = 300       # number of points
PC_MPA      = 3.0       # chamber pressure [MPa]
EPS         = 4.0       # nozzle expansion ratio
P_AMB       = 94_197.0  # ambient pressure [Pa]
# ──────────────────────────────────────────────────────────────────────────────

COLORS = ['tab:red', 'tab:blue', 'tab:green', 'tab:orange',
          'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray']


def main():
    fuel_names = SELECTED_FUELS if SELECTED_FUELS is not None else list(FUELS.keys())
    fuels  = [FUELS[n] for n in fuel_names]
    ofs    = np.linspace(OF_MIN, OF_MAX, OF_N)
    p_c_pa = PC_MPA * 1e6

    fig, (ax_tc, ax_isp) = plt.subplots(2, 1, figsize=(6, 9))
    fig.suptitle(
        f'N₂O Oxidiser - Pc = {PC_MPA:.1f} MPa,  ε = {EPS:.1f},  Pa = {P_AMB/1e3:.1f} kPa',
        fontsize=12,
    )

    tc_curves = {}   # fuel.name -> Tc array, for design-point annotation

    for fuel, color in zip(fuels, COLORS):
        props = [combustion_props(fuel, of, p_c_pa, EPS) for of in ofs]
        Tc  = np.array([p[0] for p in props])
        gam = np.array([p[1] for p in props])
        cs  = np.array([p[3] for p in props])
        cf  = np.array([thrust_coefficient(g, EPS, p_c_pa, P_AMB) for g in gam])
        isp = cf * cs / G0
        tc_curves[fuel.name] = (color, Tc)

        for ax, data, peak_fmt in [(ax_tc, Tc, '{:.0f} K'), (ax_isp, isp, '{:.0f} s')]:
            ax.plot(ofs, data, lw=2, color=color, label=fuel.name)
            pk = int(np.argmax(data))
            ax.scatter(ofs[pk], data[pk], color=color, s=60, zorder=5)
            ax.annotate(f' {peak_fmt.format(data[pk])}',
                        xy=(ofs[pk], data[pk]), fontsize=8, color=color, va='center',
                        xytext=(10,10), textcoords="offset pixels")
            of_st = fuel.of_stoich
            if OF_MIN <= of_st <= OF_MAX:
                ax.axvline(of_st, color=color, lw=0.8, ls=':', alpha=0.6)
                idx_st = int(np.searchsorted(ofs, of_st))
                ax.scatter([of_st], [data[idx_st]], color=color, s=30, marker='D', zorder=5)

    ax_tc.set_xlabel('O/F Ratio', fontsize=11)
    ax_tc.set_ylabel('Combustion Temperature (K)', fontsize=11)
    ax_tc.set_title('Adiabatic Flame Temperature', fontsize=11)
    ax_tc.legend(fontsize=10)
    ax_tc.grid(True, alpha=0.3)

    ax_isp.set_xlabel('O/F Ratio', fontsize=11)
    ax_isp.set_ylabel('Specific Impulse (s)', fontsize=11)
    ax_isp.set_title('Specific Impulse  (ideal, no efficiency)', fontsize=11)
    ax_isp.legend(fontsize=10)
    ax_isp.grid(True, alpha=0.3)

    plt.tight_layout()
    os.makedirs(PLOT_DIR, exist_ok=True)
    out = os.path.join(PLOT_DIR, 'tc_isp_vs_of.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"  Saved -> {out}")
    plt.show()


if __name__ == '__main__':
    main()
