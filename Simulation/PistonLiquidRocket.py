"""
Piston-type Liquid Rocket Engine Simulation
Propellants : Nitrous Oxide (N2O) oxidizer  +  switchable liquid fuel
Feed system :
  N2O  -- self-pressurising two-phase tank (liquid + vapour coexist at saturation).
           Feed pressure = saturation pressure P_sat(T) from CoolProp.
           Adiabatic mode : tank cools as liquid drains -> P_sat drops over the burn.
           Isothermal mode: surroundings supply heat, T and P_sat stay constant.
  Fuel -- pressurised piston tank driven by N2O vapour space (or separate N2).

Physics model
  - Combustion : rocketCEA (NASA CEA equilibrium) when available;
                 polynomial CEA fits as fallback.
  - Fuel / N2O liquid density from CoolProp where the fluid is supported.
  - N2O two-phase saturation thermodynamics via CoolProp.
  - Adiabatic energy balance for N2O tank temperature evolution.
  - Choked nozzle mass flow (isentropic 1-D).
  - Thrust coefficient CF with full pressure-area term.

Supported fuels  (pass via --fuel or EngineConfig.fuel)
  IPA      -- Isopropyl alcohol        (C3H8O)
  Ethanol  -- Ethanol                  (C2H6O)
  Methanol -- Methanol                 (CH4O)
  E85      -- 85% ethanol / 15% iso-octane blend

Usage
  python PistonLiquidRocket.py                         # default config
  python PistonLiquidRocket.py --fuel Ethanol          # switch fuel
  python PistonLiquidRocket.py --sweep                 # O/F sensitivity sweep
"""

import argparse
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
import os
plt.style.use('ggplot')

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dataclasses import dataclass, field
from typing import Optional

try:
    from CoolProp.CoolProp import PropsSI as _CP
except ImportError:
    raise SystemExit(
        "CoolProp is required.\n  pip install CoolProp"
    )

_ROCKETCEA_AVAILABLE = False
_cea_add_fuel = None
_CeaObj       = None
try:
    from rocketcea.cea_obj import CEA_Obj as _CeaObj, add_new_fuel as _cea_add_fuel
    _ROCKETCEA_AVAILABLE = True
except ImportError:
    pass

# ── Physical constants ─────────────────────────────────────────────────────────
R_UNIV = 8314.46   # J / (kmol*K)
G0     = 9.80665   # m/s^2
ATM    = 101_325   # Pa

# ── N2O fluid ─────────────────────────────────────────────────────────────────
N2O_MW    = 44.013           # g/mol
N2O_FLUID = "NitrousOxide"  # CoolProp identifier

# ── Plot output directory ──────────────────────────────────────────────────────
PLOT_DIR = os.getcwd()


# ═══════════════════════════════════════════════════════════════════════════════
#   N2O saturation property table  (built once, queried via numpy interp)
# ═══════════════════════════════════════════════════════════════════════════════

class N2OThermoTable:
    """
    Pre-tabulated N2O saturation properties on a uniform T grid.

    Replaces per-call CoolProp lookups with fast np.interp.
    For the energy-balance inversion (finding T given U) the entire
    U(T) array is evaluated at once and np.searchsorted locates the bracket
    in a single vectorised pass -- no iteration needed.

    Build cost: ~1000 CoolProp calls (~1 s).  Query cost: O(log n) numpy.
    """
    T_MIN, T_MAX, N = 183.0, 309.5, 1000

    def __init__(self):
        T = np.linspace(self.T_MIN, self.T_MAX, self.N)
        self.T       = T
        self.rho_liq = np.array([_CP('D', 'T', t, 'Q', 0, N2O_FLUID) for t in T])
        self.rho_vap = np.array([_CP('D', 'T', t, 'Q', 1, N2O_FLUID) for t in T])
        self.u_liq   = np.array([_CP('U', 'T', t, 'Q', 0, N2O_FLUID) for t in T])
        self.u_vap   = np.array([_CP('U', 'T', t, 'Q', 1, N2O_FLUID) for t in T])
        self.h_liq   = np.array([_CP('H', 'T', t, 'Q', 0, N2O_FLUID) for t in T])
        self.p_sat   = np.array([_CP('P', 'T', t, 'Q', 0, N2O_FLUID) for t in T])

    def at(self, T: float):
        Tv = self.T
        return (
            float(np.interp(T, Tv, self.rho_liq)),
            float(np.interp(T, Tv, self.rho_vap)),
            float(np.interp(T, Tv, self.u_liq)),
            float(np.interp(T, Tv, self.u_vap)),
            float(np.interp(T, Tv, self.h_liq)),
            float(np.interp(T, Tv, self.p_sat)),
        )

    def find_T_for_U(self, U_target: float, m_liq: float, volume: float) -> float:
        V_vap = np.maximum(0.0, volume - m_liq / self.rho_liq)
        U_arr = m_liq * self.u_liq + self.rho_vap * V_vap * self.u_vap
        # np.interp clamps to boundary values — prevents out-of-range extrapolation
        return float(np.interp(U_target, U_arr, self.T))


_TABLE: Optional[N2OThermoTable] = None

def _get_table() -> N2OThermoTable:
    global _TABLE
    if _TABLE is None:
        print("  Building N2O property table...", end=" ", flush=True)
        t0     = time.perf_counter()
        _TABLE = N2OThermoTable()
        print(f"done ({time.perf_counter() - t0:.2f} s)")
    return _TABLE


# ═══════════════════════════════════════════════════════════════════════════════
#   Fuel definition
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Fuel:
    """
    Fuel propellant definition.

    Combustion properties (Tc, gamma, MW, c*) come from rocketCEA when available.
    The polynomial fields are fallbacks used when rocketCEA is not installed.
    Liquid density comes from CoolProp (if coolprop_name is set) or density_ref.
    """
    name          : str
    cea_name      : str            # name registered with rocketCEA
    cea_card      : str            # thermochemical card string for rocketCEA
    coolprop_name : Optional[str]  # CoolProp fluid identifier; None = use density_ref
    density_ref   : float          # liquid density at ~20 C, 1 atm [kg/m^3]
    mw_g_mol      : float          # molecular weight [g/mol]
    n_o2_stoich   : float          # mol O2 required per mol fuel (complete combustion)

    # Polynomial fallbacks (N2O oxidiser, fitted to CEA, used if rocketCEA absent)
    t_ad_peak    : float = 3180.0
    t_ad_of_peak : float = 5.8
    t_ad_sigma   : float = 1.85
    t_ad_floor   : float = 1500.0
    mw_exh_a     : float = 20.5    # exhaust MW = a + b*OF
    mw_exh_b     : float = 1.15
    gamma_a      : float = 1.225   # exhaust gamma = a - b*(OF-4)
    gamma_b      : float = 0.006

    def liquid_density(self, T_K: float = 293.0, P_Pa: float = ATM) -> float:
        """Liquid density [kg/m^3] at (T_K, P_Pa) via CoolProp, or fallback."""
        if self.coolprop_name:
            try:
                return float(_CP('D', 'T', T_K, 'P', P_Pa, self.coolprop_name))
            except Exception:
                pass
        return self.density_ref

    @property
    def of_stoich(self) -> float:
        """Stoichiometric O/F ratio with N2O as oxidiser."""
        return 2.0 * self.n_o2_stoich * N2O_MW / self.mw_g_mol


# ── Predefined fuels ──────────────────────────────────────────────────────────
# Enthalpies of formation from NIST WebBook (liquid phase, 298.15 K).

IPA = Fuel(
    name='IPA', cea_name='IPA',
    cea_card="""
fuel IPA  C 3 H 8 O 1   wt%=100.
  h,Kcal=-76.030  t(K)=298.15  rho,g/cc=0.786
""",
    coolprop_name=None,    # 2-propanol not in CoolProp pure-fluid list
    density_ref=786.0,
    mw_g_mol=60.096,
    n_o2_stoich=4.5,       # C3H8O + 4.5 O2 -> 3CO2 + 4H2O
    t_ad_peak=3180.0, t_ad_of_peak=5.8, t_ad_sigma=1.85, t_ad_floor=1500.0,
    mw_exh_a=20.5, mw_exh_b=1.15, gamma_a=1.225, gamma_b=0.006,
)

ETHANOL = Fuel(
    name='Ethanol', cea_name='ETHANOL',
    cea_card="""
fuel ETHANOL  C 2 H 6 O 1   wt%=100.
  h,Kcal=-66.350  t(K)=298.15  rho,g/cc=0.789
""",
    coolprop_name='Ethanol',
    density_ref=789.0,
    mw_g_mol=46.069,
    n_o2_stoich=3.0,       # C2H6O + 3 O2 -> 2CO2 + 3H2O
    t_ad_peak=3220.0, t_ad_of_peak=5.5, t_ad_sigma=1.80, t_ad_floor=1500.0,
    mw_exh_a=19.5, mw_exh_b=1.20, gamma_a=1.225, gamma_b=0.005,
)

METHANOL = Fuel(
    name='Methanol', cea_name='METHANOL',
    cea_card="""
fuel METHANOL  C 1 H 4 O 1   wt%=100.
  h,Kcal=-57.152  t(K)=298.15  rho,g/cc=0.791
""",
    coolprop_name='Methanol',
    density_ref=791.0,
    mw_g_mol=32.042,
    n_o2_stoich=1.5,       # CH4O + 1.5 O2 -> CO2 + 2H2O
    t_ad_peak=3100.0, t_ad_of_peak=4.2, t_ad_sigma=1.60, t_ad_floor=1400.0,
    mw_exh_a=18.0, mw_exh_b=1.30, gamma_a=1.230, gamma_b=0.005,
)

E85 = Fuel(
    # E85: 85 vol% ethanol (C2H6O) + 15 vol% iso-octane (C8H18) as gasoline surrogate.
    # Effective blend density: 0.85*789 + 0.15*692 = 774 kg/m^3
    # Effective MW and stoichiometry derived from volume-weighted composition.
    #   Mass fractions: ethanol 86.6 wt%, iso-octane 13.4 wt%
    #   n_O2 per gram: 0.866*(3/46.07) + 0.134*(12.5/114.23) = 0.07109 mol/g
    #   Effective MW ~ 50.0 g/mol  =>  n_o2_stoich = 0.07109 * 50.0 = 3.555
    name='E85', cea_name='E85',
    cea_card="""
fuel E85  C 2 H 6 O 1   wt%=86.600
  h,Kcal=-66.350  t(K)=298.15  rho,g/cc=0.789
fuel E85  C 8 H 18       wt%=13.400
  h,Kcal=-61.960  t(K)=298.15  rho,g/cc=0.692
""",
    coolprop_name=None,
    density_ref=774.0,
    mw_g_mol=50.0,
    n_o2_stoich=3.555,
    t_ad_peak=3210.0, t_ad_of_peak=5.8, t_ad_sigma=1.82, t_ad_floor=1500.0,
    mw_exh_a=20.2, mw_exh_b=1.18, gamma_a=1.225, gamma_b=0.006,
)

ACETONE = Fuel(
    name='Acetone', cea_name='ACETONE',
    cea_card="""
fuel ACETONE  C 3 H 6 O 1   wt%=100.
  h,Kcal=-59.35  t(K)=298.15  rho,g/cc=0.791
""",
    coolprop_name='Acetone',
    density_ref=791.0,
    mw_g_mol=58.079,
    n_o2_stoich=4.0,        # C3H6O + 4 O2 -> 3CO2 + 3H2O
    t_ad_peak=3160.0, t_ad_of_peak=5.7, t_ad_sigma=1.80, t_ad_floor=1500.0,
    mw_exh_a=20.4, mw_exh_b=1.16, gamma_a=1.225, gamma_b=0.006,
)

DIESEL = Fuel(
    name='Diesel', cea_name='DIESEL',
    cea_card="""
fuel DIESEL  C 12 H 26   wt%=100.
  h,Kcal=-83.9  t(K)=298.15  rho,g/cc=0.820
""",
    coolprop_name=None,
    density_ref=820.0,
    mw_g_mol=170.34,
    n_o2_stoich=18.5,      # C12H26 + 18.5 O2 -> 12CO2 + 13H2O
    t_ad_peak=3150.0, t_ad_of_peak=9.2, t_ad_sigma=2.50, t_ad_floor=1500.0,
    mw_exh_a=21.0, mw_exh_b=0.85, gamma_a=1.225, gamma_b=0.006,
)

FUELS: dict[str, Fuel] = {
    'IPA':      IPA,
    'Ethanol':  ETHANOL,
    'Methanol': METHANOL,
    'E85':      E85,
    'Acetone':  ACETONE,
    'Diesel':   DIESEL,
}

# ── Default fuel ──────────────────────────────────────────────────────────────
# Change this line to switch fuels without touching EngineConfig.
# Options: IPA, ETHANOL, METHANOL, E85, ACETONE
DEFAULT_FUEL: Fuel = IPA


# ═══════════════════════════════════════════════════════════════════════════════
#   Engine configuration  ← edit values here
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EngineConfig:
    # Combined tank volume (ox + fuel sections share one tube separated by a piston).
    # ox_tank_volume and fuel_tank_volume are derived in __post_init__ from this value,
    # the O/F ratio, propellant densities, and ullage fraction.
    tank_volume      : float         = 4.5e-3  # m^3  total internal volume (ox + fuel)
    ox_tank_diam     : float         = 0.0952  # m  (cylindrical tank inner diameter)
    ox_ullage        : float         = 0.05    # initial vapour volume fraction [-]
    n2o_init_temp_K  : float         = 283.15  # K  (50 F / 10 C, HalfCatSim default)


    # Injector geometry  (A values = None means auto-sized from design O/F and target dP)
    # Cd values match HalfCatSim hardware; areas solved analytically to hit
    # Pc=218.6 psi and O/F=2.77 at 283.15 K N2O with 15 psi piston loss.
    cd_ox        : float          = 0.40    # discharge coefficient, N2O orifice(s)
    cd_fuel      : float          = 0.55    # discharge coefficient, fuel orifice(s)
    A_inj_ox     : Optional[float] = None   # total N2O injector area [m^2]
    A_inj_fuel   : Optional[float] = None   # total fuel injector area [m^2]
    inj_target_dp: float          = 0.20    # dP/P_feed fraction used for auto-sizing

    # Oxidiser (N2O) feed line  — pipe geometry + in-line valve
    ox_line_id       : float = 7.94e-3  # inner diameter [m];  0 = no feed-line loss
    ox_line_length   : float = 0.304    # total length [m]
    ox_line_roughness: float = 1.5e-6   # wall roughness [m]  (smooth drawn tube default)
    ox_valve_Cd      : float = 0.8      # valve discharge coefficient [-];  0 = no valve
    ox_valve_diam    : float = 0.01     # valve bore diameter [m]

    # Fuel feed line  — pipe geometry + in-line valve
    fuel_line_id       : float = 5.715e-3
    fuel_line_length   : float = 1.219
    fuel_line_roughness: float = 1.5e-6
    fuel_valve_Cd      : float = 0.8
    fuel_valve_diam    : float = 0.01

    # O/F and fuel
    of_ratio         : float          = 2.1
    fuel             : Optional[Fuel] = field(default=None)  # None -> DEFAULT_FUEL in __post_init__
    cstar_eta        : float          = 0.65
    nozzle_eta       : float          = 0.97

    # Fuel tank
    fuel_tank_diam   : float          = ox_tank_diam   # m  (cylindrical tank inner diameter)

    # IPA piston pressurant
    ipa_uses_n2o_p   : bool  = True
    ipa_pressurant_p : float = 6.0e6
    ipa_blowdown     : bool  = True
    ipa_polytropic_n : float = 1.0
    piston_dp        : float = 103_421.0  # piston seal pressure loss [Pa] (15 psi, HalfCatSim)

    # Nozzle geometry
    throat_diam      : float = 0.0254   # m
    AeAt             : float = 4
    exit_diam        : float = throat_diam*AeAt**0.5

    # Environment
    p_ambient        : float = 94_197.0  # Pa  (2000 ft / 13.664 psi, HalfCatSim default)

    def __post_init__(self):
        if self.fuel is None:
            self.fuel = DEFAULT_FUEL

        rho_liq_0 = _CP('D', 'T', self.n2o_init_temp_K, 'Q', 0, N2O_FLUID)
        rho_vap_0 = _CP('D', 'T', self.n2o_init_temp_K, 'Q', 1, N2O_FLUID)
        rho_ox_avg = rho_liq_0 * (1.0 - self.ox_ullage) + rho_vap_0 * self.ox_ullage
        headspace = 1.05 if self.ipa_uses_n2o_p else 1.25

        # Split tank_volume into ox and fuel sections.
        # fuel_tank_volume = (ox_mass / of_ratio) / rho_fuel * headspace
        #                  = rho_ox_avg * ox_vol * headspace / (of_ratio * rho_fuel)
        #                  = k * ox_vol
        # ox_vol + k * ox_vol = tank_volume  =>  ox_vol = tank_volume / (1 + k)
        k = rho_ox_avg * headspace / (self.of_ratio * self.fuel.liquid_density())
        self.ox_tank_volume   = self.tank_volume / (1.0 + k)
        self.fuel_tank_volume = self.tank_volume - self.ox_tank_volume

        self.ox_mass   = rho_ox_avg * self.ox_tank_volume
        self.fuel_mass = self.ox_mass / self.of_ratio

        # Tank lengths derived from volume and diameter (cylindrical assumption)
        _ox_A   = np.pi / 4.0 * self.ox_tank_diam ** 2
        _fuel_A = np.pi / 4.0 * self.fuel_tank_diam ** 2
        self.ox_tank_length   = self.ox_tank_volume   / _ox_A
        self.fuel_tank_length = self.fuel_tank_volume / _fuel_A

        # Auto-size injector areas if not provided.
        # Uses design O/F and target dP to size both injectors proportionally.
        if self.A_inj_ox is None or self.A_inj_fuel is None:
            rho_ox = _CP('D', 'T', self.n2o_init_temp_K, 'Q', 0, N2O_FLUID)
            rho_fuel = self.fuel.liquid_density()
            p_sat_0 = _CP('P', 'T', self.n2o_init_temp_K, 'Q', 0, N2O_FLUID)
            # Estimate initial chamber pressure from target dP
            p_c_nom = p_sat_0 * (1.0 - self.inj_target_dp)
            A_t = np.pi / 4.0 * self.throat_diam ** 2
            _, _, _, cstar_nom = combustion_props(self.fuel, self.of_ratio, p_c_nom,
                                                   (self.exit_diam / self.throat_diam)**2)
            cstar = cstar_nom * self.cstar_eta
            k_mdot_nozzle = A_t / cstar
            mdot_nozzle_nom = k_mdot_nozzle * p_c_nom

            # Split by O/F ratio
            mdot_ox_nom = mdot_nozzle_nom * self.of_ratio / (1.0 + self.of_ratio)
            mdot_fuel_nom = mdot_nozzle_nom / (1.0 + self.of_ratio)

            # Orifice equation: ṁ = Cd * A * √(2 * ρ * ΔP)
            # Solve for A: A = ṁ / (Cd * √(2 * ρ * ΔP))
            # Fuel feed pressure is lower than N2O by the piston pressure drop.
            dp_ox_nom   = p_sat_0 * self.inj_target_dp
            dp_fuel_nom = (dp_ox_nom - self.piston_dp
                           if self.ipa_uses_n2o_p else dp_ox_nom)
            if self.A_inj_ox is None:
                self.A_inj_ox = mdot_ox_nom / (
                    self.cd_ox * np.sqrt(2.0 * rho_ox * dp_ox_nom) + 1e-12)
            if self.A_inj_fuel is None:
                self.A_inj_fuel = mdot_fuel_nom / (
                    self.cd_fuel * np.sqrt(2.0 * rho_fuel * dp_fuel_nom) + 1e-12)


# ── rocketCEA object cache ────────────────────────────────────────────────────
_CEA_REGISTERED = False
_CEA_CACHE: dict[str, object] = {}

def _get_cea(fuel: Fuel) -> Optional[object]:
    """Return a cached rocketCEA CEA_Obj for this fuel, or None if unavailable."""
    if not _ROCKETCEA_AVAILABLE:
        return None
    global _CEA_REGISTERED
    if not _CEA_REGISTERED:
        for f in FUELS.values():
            try:
                _cea_add_fuel(f.cea_name, f.cea_card)
            except Exception:
                pass
        _CEA_REGISTERED = True
    if fuel.name not in _CEA_CACHE:
        try:
            _CEA_CACHE[fuel.name] = _CeaObj(oxName='N2O', fuelName=fuel.cea_name)
        except Exception:
            _CEA_CACHE[fuel.name] = None
    return _CEA_CACHE[fuel.name]


# ── Combustion property lookup ────────────────────────────────────────────────

def combustion_props(fuel: Fuel, of: float,
                     p_c_pa: float, eps: float) -> tuple[float, float, float, float]:
    """
    Return (T_c [K], gamma, mw [g/mol], cstar_ideal [m/s]) for the given
    fuel, O/F, chamber pressure, and expansion ratio.

    Uses rocketCEA (equilibrium) when available; falls back to polynomial fits.
    """
    cea = _get_cea(fuel)
    if cea is not None:
        try:
            p_psia = p_c_pa / 6894.76
            # Returns: Isp_vac[s], cstar[ft/s], Tc[R], MW[g/mol], gamma
            _, cstar_fps, Tc_R, mw, gamma = cea.get_IvacCstrTc_ChmMwGam(
                Pc=p_psia, MR=of, eps=eps
            )
            return Tc_R * 5.0/9.0, gamma, mw, cstar_fps * 0.3048
        except Exception:
            pass

    # Polynomial fallback
    T_ad  = (fuel.t_ad_floor
             + (fuel.t_ad_peak - fuel.t_ad_floor)
             * np.exp(-0.5 * ((of - fuel.t_ad_of_peak) / fuel.t_ad_sigma) ** 2))
    gamma = fuel.gamma_a - fuel.gamma_b * (of - 4.0)
    mw    = fuel.mw_exh_a + fuel.mw_exh_b * of
    R_s   = R_UNIV / mw
    cstar = np.sqrt(R_s * T_ad / gamma) * ((gamma + 1) / 2.0) ** ((gamma + 1) / (2.0 * (gamma - 1)))
    return T_ad, gamma, mw, cstar


# ═══════════════════════════════════════════════════════════════════════════════
#   Isentropic nozzle
# ═══════════════════════════════════════════════════════════════════════════════

def exit_mach(area_ratio: float, gamma: float, tol: float = 1e-9) -> float:
    """Supersonic exit Mach from area ratio (Newton's method)."""
    def eps(M):
        t   = 1.0 + (gamma - 1) / 2.0 * M * M
        exp = (gamma + 1) / (2.0 * (gamma - 1))
        return (1.0 / M) * (2.0 / (gamma + 1) * t) ** exp

    M = 2.5
    for _ in range(200):
        f   = eps(M) - area_ratio
        t   = 1.0 + (gamma - 1) / 2.0 * M * M
        exp = (gamma + 1) / (2.0 * (gamma - 1))
        A   = (2.0 / (gamma + 1)) ** exp
        dA  = A * (exp * t ** (exp - 1) * (gamma - 1) * M) - A * t ** exp / (M * M)
        M  -= f / dA
        if abs(f) < tol:
            break
    return M

def thrust_coefficient(gamma: float, area_ratio: float,
                        p_chamber: float, p_ambient: float) -> float:
    """Ideal CF including pressure-area term."""
    Me      = exit_mach(area_ratio, gamma)
    exp     = gamma / (gamma - 1)
    pe_frac = (1.0 + (gamma - 1) / 2.0 * Me ** 2) ** (-exp)
    cf_mom  = np.sqrt(2.0 * gamma**2 / (gamma - 1)
                      * (2.0 / (gamma + 1)) ** ((gamma + 1) / (gamma - 1))
                      * (1.0 - pe_frac ** ((gamma - 1) / gamma)))
    return cf_mom + (pe_frac - p_ambient / p_chamber) * area_ratio


# ═══════════════════════════════════════════════════════════════════════════════
#   N2O self-pressurising tank
# ═══════════════════════════════════════════════════════════════════════════════

class N2OSelfPressTank:
    """
    Two-phase N2O tank that pressurises itself through liquid/vapour equilibrium.

    State variables: T (bulk temperature), m_liq (liquid mass).
    Vapour mass m_vap follows from the fixed volume constraint.

    Adiabatic energy balance:  U_new = U_old - h_liq(T_old) * dm_out
    T_new found via vectorised searchsorted over the pre-built property table.
    """

    def __init__(self, mass: float, volume: float, T_init: float = 293.0):
        self.volume = volume
        self.T      = float(T_init)
        self._tbl   = _get_table()

        rho_liq, rho_vap, *_ = self._tbl.at(T_init)
        denom = 1.0/rho_liq - 1.0/rho_vap
        m_liq = (volume - mass / rho_vap) / denom
        m_vap = mass - m_liq

        if m_liq <= 0:
            raise ValueError(
                f"N2O tank: all vapour at T={T_init} K -- "
                f"reduce propellant mass or increase tank volume "
                f"(m_liq came out {m_liq:.3f} kg)."
            )
        if m_vap < 0:
            raise ValueError(
                f"N2O tank: no vapour headspace at T={T_init} K -- "
                f"increase tank volume (m_vap came out {m_vap:.3f} kg)."
            )
        self.m_liq = m_liq
        self.m_vap = m_vap

    @property
    def mass_remaining(self) -> float:
        return self.m_liq

    def feed_pressure(self) -> float:
        return float(np.interp(self.T, self._tbl.T, self._tbl.p_sat))

    def consume(self, dm: float):
        dm = min(dm, self.m_liq)
        if dm <= 0:
            return
        tbl = self._tbl
        _, _, u_liq, u_vap, h_liq, _ = tbl.at(self.T)
        U_target  = self.m_liq * u_liq + self.m_vap * u_vap - h_liq * dm
        m_liq_new = self.m_liq - dm

        T_new       = tbl.find_T_for_U(U_target, m_liq_new, self.volume)
        rho_liq_new = float(np.interp(T_new, tbl.T, tbl.rho_liq))
        rho_vap_new = float(np.interp(T_new, tbl.T, tbl.rho_vap))
        self.T     = T_new
        self.m_liq = m_liq_new
        self.m_vap = rho_vap_new * (self.volume - m_liq_new / rho_liq_new)


# ═══════════════════════════════════════════════════════════════════════════════
#   Fuel piston tank
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PistonTank:
    """Fuel tank with a piston separating propellant from pressurant gas."""
    propellant_mass    : float
    propellant_density : float
    tank_volume        : float
    pressurant_pressure: float
    blowdown           : bool
    polytropic_n       : float = 1.0

    def __post_init__(self):
        prop_vol = self.propellant_mass / self.propellant_density
        self._gas_vol_0 = self.tank_volume - prop_vol
        if self._gas_vol_0 <= 0:
            raise ValueError(
                f"Fuel tank too small: {prop_vol*1e3:.2f} L propellant "
                f"exceeds {self.tank_volume*1e3:.2f} L tank."
            )
        self._mass = self.propellant_mass

    def feed_pressure(self) -> float:
        if not self.blowdown:
            return self.pressurant_pressure
        vol_used = (self.propellant_mass - self._mass) / self.propellant_density
        gas_vol  = self._gas_vol_0 + vol_used
        return self.pressurant_pressure * (self._gas_vol_0 / gas_vol) ** self.polytropic_n

    def consume(self, dm: float):
        self._mass = max(0.0, self._mass - dm)

    @property
    def mass_remaining(self) -> float:
        return self._mass


# ═══════════════════════════════════════════════════════════════════════════════
#   Feed line hydraulic model
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FeedLine:
    """
    Hydraulic model for a feed line (hose/pipe + in-line valve), all in CdA terms.

    Pipe CdA from Darcy-Weisbach (density cancels exactly):
      CdA_pipe = A / √(f · L/D)   where f = fully-turbulent Colebrook-White limit

    Series combination with valve:
      1/CdA_eff² = 1/CdA_pipe² + 1/CdA_valve²

    f = 0.25 / [log₁₀(ε/3.7D)]²  — Re-independent (Moody chart fully-rough asymptote).
    Valid when Re > ~3500·(D/ε); holds well at propellant flow rates.
    """
    inner_diam : float = 0.0      # pipe/hose inner diameter [m]; 0 = no feed line
    length     : float = 0.0      # total pipe/hose length [m]
    roughness  : float = 1.5e-6   # absolute wall roughness [m] (smooth drawn tube default)
    valve_Cd   : float = 0.0      # valve discharge coefficient [-]; 0 = no valve loss
    valve_diam : float = 0.0      # valve bore diameter [m]

    def friction_factor(self) -> float:
        """Fully-turbulent Colebrook-White: 1/√f = −2·log₁₀(ε/3.7D)"""
        if self.inner_diam <= 0 or self.roughness <= 0:
            return 0.02
        return 0.25 / np.log10(self.roughness / (3.7 * self.inner_diam)) ** 2

    @property
    def valve_cda(self) -> float:
        """Valve CdA [m²] alone (Cd × bore area). 0 if no valve configured."""
        if self.valve_Cd > 0 and self.valve_diam > 0:
            return self.valve_Cd * np.pi / 4 * self.valve_diam ** 2
        return 0.0

    def CdA(self) -> float:
        """Effective CdA [m²] for the pipe + valve in series. Returns 0 if unconfigured."""
        if self.inner_diam <= 0:
            return 0.0
        A = np.pi / 4 * self.inner_diam ** 2
        inv_sq = 0.0
        if self.length > 0:
            CdA_pipe = A / np.sqrt(self.friction_factor() * self.length / self.inner_diam)
            inv_sq += 1.0 / CdA_pipe ** 2
        if self.valve_cda > 0:
            inv_sq += 1.0 / self.valve_cda ** 2
        return 1.0 / np.sqrt(inv_sq) if inv_sq > 0 else 0.0

    def summary(self) -> str:
        cda = self.CdA()
        parts = []
        if self.inner_diam > 0:
            parts.append(f"ID={self.inner_diam*1e3:.2f} mm")
        if self.length > 0:
            parts.append(f"L={self.length*1e3:.0f} mm  f={self.friction_factor():.4f}")
        if self.valve_Cd > 0 and self.valve_diam > 0:
            CdA_v = self.valve_Cd * np.pi / 4 * self.valve_diam ** 2
            parts.append(f"valve {self.valve_diam*1e3:.2f} mm × Cd {self.valve_Cd:.3f} = CdA {CdA_v*1e6:.3f} mm²")
        desc = "  ".join(parts) if parts else "none"
        return f"{desc}  →  CdA={cda*1e6:.3f} mm²" if cda > 0 else "none"


# ═══════════════════════════════════════════════════════════════════════════════
#   Engine simulator
# ═══════════════════════════════════════════════════════════════════════════════

class PistonEngine:

    def __init__(self, cfg: EngineConfig):
        self.cfg = cfg

        A_t = np.pi / 4.0 * cfg.throat_diam ** 2
        A_e = np.pi / 4.0 * cfg.exit_diam   ** 2
        self.A_throat        = A_t
        self.expansion_ratio = A_e / A_t

        self.ox_tank = N2OSelfPressTank(
            mass   = cfg.ox_mass,
            volume = cfg.ox_tank_volume,
            T_init = cfg.n2o_init_temp_K,
        )

        self.time        = 0.0
        self.stop_reason = "propellant exhausted"

        # ── Injector coefficients ──
        # K = Cd * A * √(2ρ)  for each propellant
        rho_ox_nom   = _CP('D', 'T', cfg.n2o_init_temp_K, 'Q', 0, N2O_FLUID)
        rho_fuel_nom = cfg.fuel.liquid_density()
        self._K_ox   = cfg.cd_ox * cfg.A_inj_ox * np.sqrt(2.0 * rho_ox_nom)
        self._K_fuel = cfg.cd_fuel * cfg.A_inj_fuel * np.sqrt(2.0 * rho_fuel_nom)

        # Build FeedLine objects from flat config params and fold into effective K
        self._feedline_ox = FeedLine(
            inner_diam=cfg.ox_line_id,   length=cfg.ox_line_length,
            roughness=cfg.ox_line_roughness,
            valve_Cd=cfg.ox_valve_Cd,    valve_diam=cfg.ox_valve_diam,
        )
        self._feedline_fuel = FeedLine(
            inner_diam=cfg.fuel_line_id, length=cfg.fuel_line_length,
            roughness=cfg.fuel_line_roughness,
            valve_Cd=cfg.fuel_valve_Cd,  valve_diam=cfg.fuel_valve_diam,
        )
        # Series combination: 1/K_eff^2 = 1/K_inj^2 + 1/K_line^2
        for fl, attr, rho in [
            (self._feedline_ox,   '_K_ox',   rho_ox_nom),
            (self._feedline_fuel, '_K_fuel', rho_fuel_nom),
        ]:
            cda = fl.CdA()
            if cda > 0:
                K_line = cda * np.sqrt(2.0 * rho)
                K_inj  = getattr(self, attr)
                setattr(self, attr, 1.0 / np.sqrt(1/K_inj**2 + 1/K_line**2))

        # ── Nozzle constants (O/F varies; use a reference design point for gamma) ──
        of_ref = cfg.of_ratio
        p_c_nom = _CP('P', 'T', cfg.n2o_init_temp_K, 'Q', 0, N2O_FLUID) * 0.8
        T_c, gamma, _, cstar_ideal = combustion_props(
            cfg.fuel, of_ref, p_c_nom, self.expansion_ratio
        )
        cstar = cstar_ideal * cfg.cstar_eta
        self._k_mdot = A_t / cstar

        # CF = cf_A - cf_B / Pc  (decompose pressure-area term)
        Me         = exit_mach(self.expansion_ratio, gamma)
        pe_over_pc = (1.0 + (gamma - 1) / 2.0 * Me ** 2) ** (-gamma / (gamma - 1))
        cf_mom     = np.sqrt(2.0 * gamma**2 / (gamma - 1)
                             * (2.0 / (gamma + 1)) ** ((gamma + 1) / (gamma - 1))
                             * (1.0 - pe_over_pc ** ((gamma - 1) / gamma)))
        self._cf_A      = (cf_mom + pe_over_pc * self.expansion_ratio) * cfg.nozzle_eta
        self._cf_B      = cfg.p_ambient * self.expansion_ratio * cfg.nozzle_eta
        self._pe_over_pc = pe_over_pc
        self._p_c_sep   = 0.4 * cfg.p_ambient / pe_over_pc

        self._cstar_nom = cstar
        self._T_c_nom   = T_c
        self._gamma_nom = gamma
        self._p_choke   = cfg.p_ambient * ((gamma + 1) / 2.0) ** (gamma / (gamma - 1))

        # ── Balance fuel mass to actual injector O/F ──────────────────────────────
        # cfg.of_ratio sizes cfg.fuel_mass, but the piston pressure drop (and any
        # feed-line losses) shift the actual O/F.  Solve for the initial Pc, compute
        # the true O/F from injector flows, then size fuel_mass to match so both
        # propellants run out simultaneously.
        p_sat_0    = _CP('P', 'T', cfg.n2o_init_temp_K, 'Q', 0, N2O_FLUID)
        p_feed_f_0 = (p_sat_0 - cfg.piston_dp
                      if cfg.ipa_uses_n2o_p else cfg.ipa_pressurant_p)
        p_c_0 = self._solve_chamber_pressure(p_sat_0, p_feed_f_0) or p_sat_0 * 0.4
        dp_ox_0    = max(0.0, p_sat_0    - p_c_0)
        dp_fuel_0  = max(0.0, p_feed_f_0 - p_c_0)
        actual_of  = (self._K_ox * np.sqrt(dp_ox_0)
                      / (self._K_fuel * np.sqrt(dp_fuel_0) + 1e-30))
        # Use m_liq (liquid only) — vapour stays as pressurant and never flows out
        fuel_mass_balanced = self.ox_tank.m_liq / actual_of
        fuel_tank_vol = cfg.fuel_tank_volume

        self._actual_of_init = actual_of
        self.fuel_tank = PistonTank(
            propellant_mass     = fuel_mass_balanced,
            propellant_density  = rho_fuel_nom,
            tank_volume         = fuel_tank_vol,
            pressurant_pressure = cfg.ipa_pressurant_p,
            blowdown            = cfg.ipa_blowdown,
            polytropic_n        = cfg.ipa_polytropic_n,
        )

        self.hist: dict[str, list] = {k: [] for k in [
            't', 'thrust', 'isp', 'mdot', 'mdot_fuel', 'mdot_ox',
            'p_chamber', 'p_feed_ox', 'p_feed_ipa', 'of_actual',
            't_chamber', 'n2o_temp', 'cstar', 'cf',
            'fuel_mass', 'ox_mass',
        ]}

    def _solve_chamber_pressure(self, p_feed_ox: float, p_feed_fuel: float) -> Optional[float]:
        """
        Solve for chamber pressure from orifice + nozzle equations.
        ṁ_ox = K_ox * √(max(0, p_feed_ox - Pc))
        ṁ_fuel = K_fuel * √(max(0, p_feed_fuel - Pc))
        ṁ_total = ṁ_ox + ṁ_fuel = k_mdot * Pc   (nozzle constraint)

        Uses Newton-Raphson to find Pc that satisfies the constraint.
        """
        # Warm-start from the previous converged Pc — one iteration usually
        # suffices for a small dt step.  Cold-start 0.7*min(p_feed) on first call.
        p_c = getattr(self, '_p_c_prev', min(p_feed_ox, p_feed_fuel) * 0.7)
        p_c = min(p_c, min(p_feed_ox, p_feed_fuel))  # must start below both feeds
        for _ in range(100):
            dp_ox   = max(0.0, p_feed_ox   - p_c)
            dp_fuel = max(0.0, p_feed_fuel - p_c)
            r = (self._K_ox   * np.sqrt(dp_ox)
                 + self._K_fuel * np.sqrt(dp_fuel)
                 - self._k_mdot * p_c)
            if abs(r) < 1e-3:
                break
            drdp = self._k_mdot
            if dp_ox   > 0: drdp += self._K_ox   * 0.5 / np.sqrt(dp_ox)
            if dp_fuel > 0: drdp += self._K_fuel * 0.5 / np.sqrt(dp_fuel)
            p_c = max(0.0, p_c + r / drdp)
        dp_ox   = max(0.0, p_feed_ox   - p_c)
        dp_fuel = max(0.0, p_feed_fuel - p_c)
        r_final = (self._K_ox * np.sqrt(dp_ox) + self._K_fuel * np.sqrt(dp_fuel)
                   - self._k_mdot * p_c)
        if abs(r_final) >= 1e-2:
            return None
        self._p_c_prev = p_c
        return float(p_c)

    def step(self, dt: float) -> Optional[dict]:
        if self.fuel_tank.mass_remaining < 1e-5 or self.ox_tank.mass_remaining < 1e-5:
            return None

        p_feed_ox  = self.ox_tank.feed_pressure()
        p_feed_fuel = (p_feed_ox - self.cfg.piston_dp
                       if self.cfg.ipa_uses_n2o_p
                       else self.fuel_tank.feed_pressure())

        # Solve for chamber pressure
        p_c = self._solve_chamber_pressure(p_feed_ox, p_feed_fuel)
        if p_c is None or p_c < self._p_choke:
            if p_c is None:
                reason = "could not converge chamber pressure"
            else:
                reason = f"nozzle unchoked (Pc={p_c/1e5:.2f} bar < {self._p_choke/1e5:.2f} bar)"
            self.stop_reason = f"{reason} at t={self.time:.3f} s"
            return None

        if p_c < self._p_c_sep:
            p_exit = self._pe_over_pc * p_c
            self.stop_reason = (
                f"flow separation at t={self.time:.3f} s "
                f"(Pe={p_exit/1e5:.3f} bar = {100*p_exit/self.cfg.p_ambient:.1f}% Pa)"
            )
            return None

        # Compute mass flow rates
        dp_ox = max(0.0, p_feed_ox - p_c)
        dp_fuel = max(0.0, p_feed_fuel - p_c)
        mdot_ox = self._K_ox * np.sqrt(dp_ox)
        mdot_fuel = self._K_fuel * np.sqrt(dp_fuel)
        mdot = mdot_ox + mdot_fuel

        # Actual O/F and combustion properties
        of_actual = mdot_ox / (mdot_fuel + 1e-12) if mdot_fuel > 1e-6 else 1e6
        T_c, _, _, cstar_ideal = combustion_props(
            self.cfg.fuel, of_actual, p_c, self.expansion_ratio
        )
        cstar = cstar_ideal * self.cfg.cstar_eta

        # Thrust calculation
        cf = self._cf_A - self._cf_B / p_c
        thrust = cf * p_c * self.A_throat
        isp = thrust / (mdot * G0) if mdot > 0 else 0.0

        # Propellant consumption
        dm_ox = mdot_ox * dt
        dm_fuel = mdot_fuel * dt
        frac = min(
            self.ox_tank.mass_remaining / (dm_ox + 1e-12),
            self.fuel_tank.mass_remaining / (dm_fuel + 1e-12),
            1.0,
        )
        dm_ox *= frac;  dm_fuel *= frac
        mdot *= frac;  thrust *= frac
        mdot_ox *= frac;  mdot_fuel *= frac

        self.ox_tank.consume(dm_ox)
        self.fuel_tank.consume(dm_fuel)
        self.time += dt

        state = dict(
            t          = self.time,
            thrust     = thrust,
            isp        = isp,
            mdot       = mdot,
            mdot_fuel  = mdot_fuel,
            mdot_ox    = mdot_ox,
            p_chamber  = p_c,
            p_feed_ox  = p_feed_ox,
            p_feed_ipa = p_feed_fuel,
            of_actual  = of_actual,
            t_chamber  = T_c,
            n2o_temp   = self.ox_tank.T,
            cstar      = cstar,
            cf         = cf,
            fuel_mass  = self.fuel_tank.mass_remaining,
            ox_mass    = self.ox_tank.mass_remaining,
        )
        for k, v in state.items():
            self.hist[k].append(v)
        return state

    def run(self, dt: float = 0.01) -> dict:
        while self.fuel_tank.mass_remaining > 1e-5 and self.ox_tank.mass_remaining > 1e-5:
            if self.step(dt) is None:
                break
        return self.hist


# ═══════════════════════════════════════════════════════════════════════════════
#   Reporting and plotting
# ═══════════════════════════════════════════════════════════════════════════════

def print_config(cfg: EngineConfig, eng: PistonEngine):
    T0        = cfg.n2o_init_temp_K
    p_sat_0   = _CP('P', 'T', T0, 'Q', 0, N2O_FLUID)
    rho_liq_0 = _CP('D', 'T', T0, 'Q', 0, N2O_FLUID)
    rho_vap_0 = _CP('D', 'T', T0, 'Q', 1, N2O_FLUID)
    p_choke   = cfg.p_ambient * ((eng._gamma_nom + 1) / 2.0) ** (eng._gamma_nom / (eng._gamma_nom - 1))

    src = "rocketCEA" if _ROCKETCEA_AVAILABLE else "polynomial fallback"
    sep = "-" * 62
    print()
    print(sep)
    print(f"  N2O / {cfg.fuel.name} piston rocket  "
          f"(combustion props: {src})")
    print(sep)
    print("  N2O oxidiser tank  (self-pressurising, two-phase)")
    print(f"    Initial temperature  : {T0:.1f} K  ({T0-273.15:.1f} C)")
    print(f"    Saturation pressure  : {p_sat_0/1e6:.3f} MPa  ({p_sat_0/6894.76:.0f} psi)")
    print(f"    Liquid density       : {rho_liq_0:.1f} kg/m^3")
    print(f"    Vapour density       : {rho_vap_0:.1f} kg/m^3")
    V_vap_init = eng.ox_tank.m_vap / _CP('D', 'T', T0, 'Q', 1, N2O_FLUID)
    ullage_pct = 100.0 * V_vap_init / cfg.ox_tank_volume
    print(f"    Liquid / vapour mass : {eng.ox_tank.m_liq:.3f} kg  /  {eng.ox_tank.m_vap:.3f} kg")
    print(f"    Ullage (vapour vol)  : {ullage_pct:.1f}%  ({V_vap_init*1e3:.2f} L vapour)")
    print(f"    Volume / diameter    : {cfg.ox_tank_volume*1e3:.2f} L  /  {cfg.ox_tank_diam*1e3:.0f} mm"
          f"  (of {cfg.tank_volume*1e3:.2f} L total)")
    print(f"    Length               : {cfg.ox_tank_length*1e3:.0f} mm")
    print(f"    Thermal model        : adiabatic (T drops as liquid drains)")
    print(f"  {cfg.fuel.name} fuel tank  (piston)")
    print(f"    Density              : {cfg.fuel.liquid_density():.1f} kg/m^3"
          f"  (CoolProp)" if cfg.fuel.coolprop_name else "    Density              : "
          f"{cfg.fuel.liquid_density():.1f} kg/m^3  (reference value)")
    print(f"    Volume / diameter    : {cfg.fuel_tank_volume*1e3:.2f} L  /  {cfg.fuel_tank_diam*1e3:.0f} mm")
    print(f"    Length               : {cfg.fuel_tank_length*1e3:.0f} mm")
    if cfg.ipa_uses_n2o_p:
        print(f"    Pressurant           : N2O vapour space (always equal to N2O feed P)")
    else:
        ipa_margin = cfg.ipa_pressurant_p - p_sat_0
        print(f"    Pressurant           : separate N2  {cfg.ipa_pressurant_p/1e6:.3f} MPa  "
              f"({'blowdown' if cfg.ipa_blowdown else 'regulated'})")
        flag = f"+{ipa_margin/1e6:.3f} MPa margin" if ipa_margin >= 0 else \
               f"{ipa_margin/1e6:.3f} MPa  ** BELOW N2O P_sat **"
        print(f"    vs N2O P_sat         : {flag}")
    print(f"  Combustion (design point)")
    print(f"    Chamber temperature  : {eng._T_c_nom:.0f} K")
    print(f"    Exhaust gamma        : {eng._gamma_nom:.4f}")
    print(f"    c* (w/ eta)          : {eng._cstar_nom:.0f} m/s")
    fl_ox   = eng._feedline_ox
    fl_fuel = eng._feedline_fuel
    print(f"  Feed lines")
    print(f"    N2O  : {fl_ox.summary()}")
    if fl_ox.valve_cda > 0:
        print(f"           valve CdA = {fl_ox.valve_cda*1e6:.3f} mm²")
    print(f"    Fuel : {fl_fuel.summary()}")
    if fl_fuel.valve_cda > 0:
        print(f"           valve CdA = {fl_fuel.valve_cda*1e6:.3f} mm²")
    print(f"  Injectors")
    print(f"    N2O  : A={cfg.A_inj_ox*1e6:.2f} mm²  Cd={cfg.cd_ox:.3f}  "
          f"CdA={cfg.cd_ox*cfg.A_inj_ox*1e6:.3f} mm²")
    print(f"    Fuel : A={cfg.A_inj_fuel*1e6:.2f} mm²  Cd={cfg.cd_fuel:.3f}  "
          f"CdA={cfg.cd_fuel*cfg.A_inj_fuel*1e6:.3f} mm²")
    print(f"  Nozzle unchoke limit    : {p_choke/1e5:.3f} bar  (Pc at which throat goes subsonic)")
    print(f"  Flow separation limit   : {eng._p_c_sep/1e5:.3f} bar  (Pe < 40% Pa, Summerfield)")
    print(f"  Design O/F ratio        : {cfg.of_ratio:.2f}  "
          f"(stoich = {cfg.fuel.of_stoich:.2f})")
    print(f"  Throat / exit           : {cfg.throat_diam*1000:.1f} mm / "
          f"{cfg.exit_diam*1000:.1f} mm  (eps={eng.expansion_ratio:.2f})")
    print(sep)


def print_summary(hist: dict, stop_reason: str = "propellant exhausted"):
    if not hist['t']:
        print(f"\n  No data produced -- {stop_reason}")
        return
    t      = hist['t']
    thrust = hist['thrust']
    isp    = hist['isp']
    J      = float(np.trapezoid(thrust, t))
    sep    = "-" * 52
    print()
    print(sep)
    print("  Performance Summary")
    print(sep)
    print(f"  Burn time           : {t[-1]:7.3f} s")
    print(f"  Avg / peak thrust   : {np.mean(thrust):7.1f} N  /  {max(thrust):.1f} N"
          f"  ({np.mean(thrust)/4.448:.1f} lbf avg)")
    print(f"  Avg Isp             : {np.mean(isp):7.2f} s")
    print(f"  Total impulse       : {J:7.1f} N*s")
    print(f"  Avg c*              : {np.mean(hist['cstar']):7.1f} m/s")
    if hist['n2o_temp']:
        T_s, T_e = hist['n2o_temp'][0], hist['n2o_temp'][-1]
        print(f"  N2O temp drop       : {T_s-T_e:7.2f} K  "
              f"({T_s-273.15:.1f} C -> {T_e-273.15:.1f} C)")
        print(f"  N2O P_sat drop      : "
              f"{hist['p_feed_ox'][0]/1e6:7.3f} -> {hist['p_feed_ox'][-1]/1e6:.3f} MPa")
    print(f"  Stopped by          :  {stop_reason}")
    print(sep)

def plot_results(hist: dict, title: str = "", fuel_name: str = "Fuel"):
    # Drop the final datapoint — it's often a partial step with a sudden drop
    hist = {k: v[:-1] if len(v) > 1 else v for k, v in hist.items()}
    t = hist['t']
    fuel_label = f"{fuel_name} (fuel)"
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fig.suptitle(f"{title if title else ''}",
                 fontsize=13, fontweight='bold')

    # ── Simple single-series panels ───────────────────────────────────────────
    panels = [
        (axes[0, 0], hist['thrust'],
         'Thrust (N)',      'Thrust',               'tab:red',   True,  None),
        (axes[0, 1], hist['isp'],
         'Isp (s)',         'Specific Impulse',     'tab:blue',  False, None),
        (axes[1, 1], [T - 273.15 for T in hist['n2o_temp']],
         'Temperature (C)', 'N2O Tank Temperature', 'tab:cyan',  False, None),
        (axes[1, 2], [f + o for f, o in zip(hist['fuel_mass'], hist['ox_mass'])],
         'Propellant (kg)', 'Propellant Remaining', 'tab:green', True, "Total"),
    ]
    for ax, data, ylabel, title_ax, color, zero_origin, label in panels:
        ax.plot(t, data, label=label, color=color, linewidth=1.8)
        ax.set_xlabel('Time (s)'); ax.set_ylabel(ylabel); ax.set_title(title_ax)
        ax.grid(True, alpha=0.3)
        if zero_origin:
            ax.set_ylim(bottom=0)

    # ── Combined pressure panel ───────────────────────────────────────────────
    ax_p = axes[0, 2]
    ax_p.plot(t, [p/1e6 for p in hist['p_feed_ox']], color='tab:orange', lw=1.8, label='Feed')
    ax_p.plot(t, [p/1e6 for p in hist['p_chamber']], color='tab:red',    lw=1.8, label='Chamber')
    ax_p.set_xlabel('Time (s)'); ax_p.set_ylabel('Pressure (MPa)'); ax_p.set_title('Pressures')
    ax_p.legend(fontsize=8); ax_p.grid(True, alpha=0.3); ax_p.set_ylim(bottom=0)

    # ── Combined mass flow panel ──────────────────────────────────────────────
    ax_m = axes[1, 0]
    ax_m.plot(t, hist['mdot'],      color='tab:green',   lw=1.8, label='Total')
    ax_m.plot(t, hist['mdot_ox'],   color='orangered',   lw=1.3, ls='--', label='N2O (ox)')
    ax_m.plot(t, hist['mdot_fuel'], color='steelblue',   lw=1.3, ls='--', label=fuel_label)
    ax_m.set_xlabel('Time (s)'); ax_m.set_ylabel('Mass Flow (kg/s)'); ax_m.set_title('Mass Flows')
    ax_m.legend(fontsize=8); ax_m.grid(True, alpha=0.3); ax_m.set_ylim(bottom=0)

    # ── Propellant remaining species overlay ──────────────────────────────────
    axes[1, 2].plot(t, hist['ox_mass'],   '--', color='orangered', lw=1.3, label='N2O (ox)')
    axes[1, 2].plot(t, hist['fuel_mass'], '--', color='steelblue', lw=1.3, label=fuel_label)
    axes[1, 2].legend(fontsize=8)

    plt.tight_layout()
    os.makedirs(PLOT_DIR, exist_ok=True)
    out = os.path.join(PLOT_DIR, 'engine_simulation.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"\n  Plot saved -> {out}")
    plt.show()


# ═══════════════════════════════════════════════════════════════════════════════
#   O/F sweep
# ═══════════════════════════════════════════════════════════════════════════════

def of_sweep(cfg: EngineConfig, of_range=(3.0, 9.0, 25)):
    ofs   = np.linspace(*of_range)
    p_sat = _CP('P', 'T', cfg.n2o_init_temp_K, 'Q', 0, N2O_FLUID)
    p_c   = p_sat * 0.8  # reference chamber pressure for sweep
    A_t   = np.pi / 4.0 * cfg.throat_diam ** 2
    eps   = (cfg.exit_diam / cfg.throat_diam) ** 2

    isps, cstars, Tcs, thrusts = [], [], [], []
    for of in ofs:
        T_c, gamma, _, cstar_id = combustion_props(cfg.fuel, of, p_c, eps)
        cstar = cstar_id * cfg.cstar_eta
        cf    = thrust_coefficient(gamma, eps, p_c, cfg.p_ambient) * cfg.nozzle_eta
        mdot  = p_c * A_t / cstar
        isps.append(cf * p_c * A_t / (mdot * G0))
        cstars.append(cstar);  Tcs.append(T_c);  thrusts.append(cf * p_c * A_t)

    of_st = cfg.fuel.of_stoich
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    fig.suptitle(f"O/F Sensitivity -- N2O / {cfg.fuel.name}", fontsize=12)
    for ax, y, ylabel, title, color in [
        (axes[0, 0], isps,    'Isp (s)',    'Specific Impulse',        'tab:blue'),
        (axes[0, 1], cstars,  'c* (m/s)',   'Characteristic Velocity', 'tab:green'),
        (axes[1, 0], Tcs,     'T_c (K)',    'Chamber Temperature',     'tab:red'),
        (axes[1, 1], thrusts, 'Thrust (N)', 'Thrust',                  'tab:orange'),
    ]:
        ax.plot(ofs, y, color=color, linewidth=2)
        ax.axvline(of_st,        color='gray',  lw=1.0, ls='--', label=f'Stoich ({of_st:.2f})')
        ax.axvline(cfg.of_ratio, color='black', lw=1.2, ls=':',  label=f'Design ({cfg.of_ratio})')
        ax.set_xlabel('O/F');  ax.set_ylabel(ylabel);  ax.set_title(title)
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    os.makedirs(PLOT_DIR, exist_ok=True)
    out = os.path.join(PLOT_DIR, 'of_sweep.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"  O/F sweep saved -> {out}")
    plt.show()


# ═══════════════════════════════════════════════════════════════════════════════
#   Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="N2O self-pressurising / fuel piston rocket engine simulator"
    )
    parser.add_argument('--sweep',          action='store_true',
                        help='Run O/F sensitivity sweep')
    parser.add_argument('--fuel', choices=list(FUELS.keys()), default=None,
                        help=f'Fuel choice: {list(FUELS.keys())}  (overrides EngineConfig default)')
    parser.add_argument('--n2o-temp',  type=float, default=None,
                        help='N2O initial temperature [deg C]  (overrides EngineConfig default)')
    parser.add_argument('--separate-ipa-press', action='store_true',
                        help='Fuel uses separate N2 pressurant (not N2O vapour space)')
    parser.add_argument('--ipa-pc',    type=float, default=None,
                        help='Separate fuel pressurant pressure [MPa]')
    parser.add_argument('--regulated', action='store_true',
                        help='Separate pressurant regulated (constant)')
    parser.add_argument('--ox-ullage', type=float, default=None,
                        help='Initial N2O vapour volume fraction [0–1]  (default 0.05)')
    parser.add_argument('--of',  type=float, default=None,
                        help='O/F ratio  (overrides EngineConfig default)')
    parser.add_argument('--dt',  type=float, default=0.01,
                        help='Time step [s]  (default 0.01)')
    args = parser.parse_args()

    overrides: dict = {}
    if args.of        is not None: overrides['of_ratio']         = args.of
    if args.n2o_temp  is not None: overrides['n2o_init_temp_K']  = args.n2o_temp + 273.15
    if args.ipa_pc    is not None: overrides['ipa_pressurant_p'] = args.ipa_pc * 1e6
    if args.fuel      is not None: overrides['fuel']             = FUELS[args.fuel]
    if args.ox_ullage is not None: overrides['ox_ullage']        = args.ox_ullage

    cfg = EngineConfig(
        ipa_uses_n2o_p   = not args.separate_ipa_press,
        ipa_blowdown     = not args.regulated,
        **overrides,
    )

    if not _ROCKETCEA_AVAILABLE:
        print("  WARNING: rocketcea not found -- using polynomial CEA fits.")
        print("           pip install rocketcea  for full accuracy.\n")

    engine = PistonEngine(cfg)
    print_config(cfg, engine)

    if args.sweep:
        print("\n  Running O/F sweep...")
        of_sweep(cfg)

    print(f"\n  Simulating (N2O adiabatic, fuel={cfg.fuel.name}, dt={args.dt} s)...")
    t0   = time.perf_counter()
    hist = engine.run(dt=args.dt)
    print(f"  Run complete in {time.perf_counter() - t0:.3f} s  ({len(hist['t'])} steps)")
    print_summary(hist, engine.stop_reason)

    if hist['t']:
        plot_results(hist, title=f"N2O/{cfg.fuel.name}  O/F={cfg.of_ratio}",
                     fuel_name=cfg.fuel.name)


if __name__ == "__main__":
    main()
