"""
Combustion temperature and Isp vs equivalence ratio lambda (= O/F / O/F_stoich).
Also generates a standalone plot of lambda vs O/F for all selected fuels.

Supported fuels
  IPA      -- Isopropyl alcohol        (C3H8O)
  Ethanol  -- Ethanol                  (C2H6O)
  Methanol -- Methanol                 (CH4O)
  E85      -- 85% ethanol / 15% iso-octane blend
  Acetone  -- Acetone                  (C3H6O)

"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PistonLiquidRocket import FUELS, combustion_props, thrust_coefficient, G0, PLOT_DIR

plt.style.use('ggplot')

# -- Configuration -------------------------------------------------------------
SELECTED_FUELS = ['IPA', 'Ethanol', 'E85', 'Acetone', 'Diesel']  # subset of FUELS, or None for all
LAM_MIN = 0.2       # lambda sweep start  (Tc/Isp plots)
LAM_MAX = 1.0       # lambda sweep end
LAM_N   = 300       # number of points
OF_MIN  = 1.0       # O/F range for lambda vs O/F reference plot
OF_MAX  = 8.0
PC_MPA  = 3.0       # chamber pressure [MPa]
EPS     = 4.0       # nozzle expansion ratio
P_AMB   = 94_197.0  # ambient pressure [Pa]
MIN_TEMP= 2000      # minimum temperature to plot [K]

# Peak label offsets in points (dx, dy) — tweak to avoid line overlap
OFFS           = 10
LABEL_OFFSET_TC  = {'IPA': (-OFFS-15, OFFS), 'Ethanol': (OFFS, OFFS-2),
                    'E85': (OFFS, -OFFS-2), 'Acetone': (-OFFS-10, -OFFS-2),
                    'Diesel': (-15, -15)}
LABEL_OFFSET_ISP = {'IPA': (4, -8), 'Ethanol': (-25, 5),
                    'E85': (4, 13), 'Acetone': (-20, -8),
                    'Diesel': (0, -12)}
# ------------------------------------------------------------------------------

COLORS = ['tab:red', 'tab:blue', 'tab:green', 'tab:orange',
          'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray']


def main():
    fuel_names = SELECTED_FUELS if SELECTED_FUELS is not None else list(FUELS.keys())
    fuels   = [FUELS[n] for n in fuel_names]
    lambdas = np.linspace(LAM_MIN, LAM_MAX, LAM_N)
    p_c_pa  = PC_MPA * 1e6

    # -- Tc and Isp vs lambda --------------------------------------------------
    fig, (ax_tc, ax_isp) = plt.subplots(2, 1, figsize=(6, 9))
    fig.suptitle(
        f'N₂O Oxidiser — Pc = {PC_MPA:.1f} MPa,  ε = {EPS:.1f},  Pa = {P_AMB/1e3:.1f} kPa',
        fontsize=12,
    )

    for fuel, color in zip(fuels, COLORS):
        ofs_fuel = lambdas * fuel.of_stoich
        props = [combustion_props(fuel, of, p_c_pa, EPS) for of in ofs_fuel]
        Tc  = np.array([p[0] for p in props])
        gam = np.array([p[1] for p in props])
        cs  = np.array([p[3] for p in props])
        cf  = np.array([thrust_coefficient(g, EPS, p_c_pa, P_AMB) for g in gam])
        isp = cf * cs / G0

        for ax, data, peak_fmt, offsets in [
            (ax_tc,  Tc,  '{:.0f} K', LABEL_OFFSET_TC),
            (ax_isp, isp, '{:.0f} s', LABEL_OFFSET_ISP),
        ]:
            ax.plot(lambdas, data, lw=2, color=color, label=fuel.name)
            pk = int(np.argmax(data))
            ax.scatter(lambdas[pk], data[pk], color=color, s=60, zorder=5)
            dx, dy = offsets.get(fuel.name, (4, 0))
            ax.annotate(peak_fmt.format(data[pk]),
                        xy=(lambdas[pk], data[pk]),
                        xytext=(dx, dy), textcoords='offset points',
                        fontsize=8, color=color, va='center')

    for ax in (ax_tc, ax_isp):
        ax.axvline(1.0, color='gray', lw=1.0, ls=':', alpha=0.8, label='Stoichiometric (λ=1)')

    ax_tc.set_xlabel('λ', fontsize=11)
    ax_tc.set_ylabel('Combustion Temperature (K)', fontsize=11)
    ax_tc.set_title('Adiabatic Flame Temperature', fontsize=11)
    ax_tc.set_ylim([MIN_TEMP, None])
    ax_tc.legend(fontsize=10)
    ax_tc.grid(True, alpha=0.3)

    ax_isp.set_xlabel('λ', fontsize=11)
    ax_isp.set_ylabel('Specific Impulse (s)', fontsize=11)
    ax_isp.set_title('Specific Impulse  (ideal, no efficiency)', fontsize=11)
    ax_isp.legend(fontsize=10)
    ax_isp.grid(True, alpha=0.3)

    plt.tight_layout()
    os.makedirs(PLOT_DIR, exist_ok=True)
    out1 = os.path.join(PLOT_DIR, 'tc_isp_vs_lambda.png')
    plt.savefig(out1, dpi=150, bbox_inches='tight')
    print(f"  Saved -> {out1}")

    # -- Standalone: lambda vs O/F for all fuels -------------------------------
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    fig2.suptitle('O/F vs λ  —  N₂O Oxidiser', fontsize=12)

    of_arr = np.linspace(OF_MIN, OF_MAX, LAM_N)
    for fuel, color in zip(fuels, COLORS):
        lam = of_arr / fuel.of_stoich
        ax2.plot(lam, of_arr, lw=2, color=color,
                 label=f'{fuel.name}  (stoich O/F = {fuel.of_stoich:.2f})')

    ax2.axvline(1.0, color='gray', lw=1.0, ls='--', alpha=0.8, label='Stoichiometric (λ=1)')
    ax2.set_xlabel('λ', fontsize=11)
    ax2.set_ylabel('O/F Ratio', fontsize=11)
    ax2.set_title('O/F = λ × O/F_stoich', fontsize=11)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out2 = os.path.join(PLOT_DIR, 'lambda_vs_of.png')
    plt.savefig(out2, dpi=150, bbox_inches='tight')
    print(f"  Saved -> {out2}")

    plt.show()


if __name__ == '__main__':
    main()
