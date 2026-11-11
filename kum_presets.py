"""Permalink (Begrenzen), Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio)."""

from dataclasses import dataclass

import streamlit as st

import kum_constants as C
from kum_rng import SplitMix64


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    lo: float | None = None
    hi: float | None = None


SETTING_SPECS = {
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
    "n_slider": SettingSpec("n", int, C.DEFAULT_N, C.N_MIN, C.N_MAX),
    "res_slider": SettingSpec("res", int, C.DEFAULT_RES, C.RES_MIN, C.RES_MAX),
    "cap_slider": SettingSpec("cap", int, C.DEFAULT_CAP, C.CAP_MIN, C.CAP_MAX),
    "budget_slider": SettingSpec("budget", int, C.DEFAULT_BUDGET, C.BUDGET_MIN, C.BUDGET_MAX),
    "hb_bsp_radio": SettingSpec("bsp", int, C.DEFAULT_HB_BSP, min(C.HB_BEISPIELE), max(C.HB_BEISPIELE)),
    "hb_h_radio": SettingSpec("h", int, C.DEFAULT_HB_H, min(C.HB_HORIZONTS), max(C.HB_HORIZONTS)),
    "hb_stufe_radio": SettingSpec("stufe", int, C.DEFAULT_HB_STAGE, min(C.STAGES), max(C.STAGES)),
    "zelle_radio": SettingSpec("zelle", int, 0, 0, len(C.CELL_KEYS) - 1),
    "sat_h_radio": SettingSpec("sat_h", int, 0, min(C.SAT_H_WAHL), max(C.SAT_H_WAHL)),
    "sat_budget_slider": SettingSpec("sat_budget", int, C.DEFAULT_SAT_BUDGET, C.SAT_BUDGET_MIN, C.SAT_BUDGET_MAX),
}
PRESET_KEYS = {"seed": "seed_input", "n": "n_slider", "res": "res_slider", "cap": "cap_slider", "budget": "budget_slider", "bsp": "hb_bsp_radio",
               "h": "hb_h_radio", "stufe": "hb_stufe_radio", "zelle": "zelle_radio", "sat_h": "sat_h_radio", "sat_budget": "sat_budget_slider"}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf die Reglergrenzen begrenzt."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
            except (ValueError, TypeError):
                continue
            if spec.lo is not None:
                value = max(spec.lo, value)
            if spec.hi is not None:
                value = min(spec.hi, value)
            st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        if key in C.PRESETS[name]:
            st.session_state[state_key] = C.PRESETS[name][key]


def aktives_preset():
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Preset ohne Eintrag für einen Regler meint dessen
    Standardwert) mit dem Session State. Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS,
    dann hebt auch seine Änderung die Markierung auf (tests/test_layout.py prüft das für jeden Regler)."""
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        if all(
            st.session_state.get(state_key, spec.default) == preset.get(preset_key_of.get(state_key), spec.default)
            for state_key, spec in SETTING_SPECS.items()
        ):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Preset ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden:")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def randomize_seed():
    """Neuer Zufalls-Seed der Instanz, selbst aus dem SplitMix64-Strom gezogen (nie Python-`random`): der Zähler der Klicks bestimmt die Folge, die Seeds sind reproduzierbar."""
    klick = st.session_state.get("seed_klicks", 0) + 1
    st.session_state["seed_klicks"] = klick
    st.session_state["seed_input"] = SplitMix64(st.session_state.get("seed_input", C.DEFAULT_SEED) * 1000 + klick).below(C.SEED_MAX + 1)
