"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen, jedes Preset verspricht, was es hält."""

import kum_algorithm as A
import kum_constants as C
import kum_evaluation as ev
import kum_presets as P
from kum_scenario import H1, H2


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_slider_bounds():
    for name, preset in C.PRESETS.items():
        for key, state_key in P.PRESET_KEYS.items():
            spec = P.SETTING_SPECS[state_key]
            assert spec.lo <= preset[key] <= spec.hi, (name, key)
        assert preset["h"] in C.HB_HORIZONTS and preset["stufe"] in C.STAGES and preset["bsp"] in C.HB_BEISPIELE


def test_default_preset_equals_the_default_settings():
    assert ev.Settings(**C.PRESETS["Handbeispiel H1 (Timetabling)"]) == ev.Settings()


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_presets_are_pairwise_different():
    """Sonst könnte das aktive Preset nicht eindeutig hervorgehoben werden."""
    werte = [tuple(sorted(p.items())) for p in C.PRESETS.values()]
    assert len(set(werte)) == len(werte)


def test_the_handbook_presets_keep_what_their_help_says():
    """H1: bei Horizont 6 scheitert Timetabling an der Wurzel, bei 7 sind P und Q im Zeitpunkt 3 voll belegt. H2: bei Horizont 7 schließt Timetabling nichts, die Energie im Fenster [0, 7) ist 15 > 2 · 7."""
    h1, h2 = C.PRESETS["Handbeispiel H1 (Timetabling)"], C.PRESETS["Handbeispiel H2 (Energie)"]
    assert (h1["bsp"], h1["h"], h1["stufe"]) == (1, 7, 1) and (h2["bsp"], h2["h"], h2["stufe"]) == (2, 7, 2)
    assert not A.fixpunkt(H1, 6, 1).ok and A.pflichtprofil(H1, *(lambda f: (f.est, f.lst))(A.fixpunkt(H1, 7, 0)), 7)[3] == 2
    f1, f2 = A.fixpunkt(H2, 7, 1), A.fixpunkt(H2, 7, 2)
    assert f1.ok and f1.z.tt_schluesse == 0 and not f2.ok and f2.z.fehl_energie == 1
    for wort in ("Zeitpunkt 3", "Horizont 6", "Kapazität 2"):
        assert wort in C.PRESET_HELP["Handbeispiel H1 (Timetabling)"]
    for wort in ("Horizont 7", "15", "2 · 7", "Bedarf 2"):
        assert wort in C.PRESET_HELP["Handbeispiel H2 (Energie)"]


def test_the_cell_presets_name_their_size_and_match_the_cells():
    for name, zelle, (n, res, cap) in (("Zelle A (n = 10)", 0, C.ZELLEN["A"]), ("Zelle B (n = 15)", 1, C.ZELLEN["B"])):
        p = C.PRESETS[name]
        assert (p["n"], p["res"], p["cap"], p["zelle"]) == (n, res, cap, zelle)
        assert f"{n} Aktivitäten" in C.PRESET_HELP[name] and f"Kapazität {cap}" in C.PRESET_HELP[name] and "Zufalls-Seed 3" in C.PRESET_HELP[name]
        assert p["seed"] == 3


def test_the_zelle_b_help_says_not_every_instance_is_proven():
    """Hilfetext Zelle B: „hier beweist nicht mehr jede Stufe jede Instanz im Budget“ gegen die vorgerechnete Reihe."""
    rows = ev.statistik(ev.lade_sweeps()["reihen"]["B"])
    assert all(r["bewiesen"] < r["n"] for r in rows)
    assert "nicht mehr jede Stufe jede Instanz im Budget" in C.PRESET_HELP["Zelle B (n = 15)"]


def test_the_sweep_parameters_are_the_documented_ones():
    assert C.SWEEP_SEEDS == tuple(range(10)) and C.SWEEP_BUDGET == 20000 and C.SAT_BUDGET == 20000 and len(C.SAT_SEEDS) == 6
    assert C.ZELLEN == {"A": (10, 1, 3), "B": (15, 1, 4), "C": (20, 2, 4), "D": (30, 2, 5)}
