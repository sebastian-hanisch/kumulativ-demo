"""Live-Knöpfe: Zwischenspeicher und Fortschrittsanzeige (kum_live.py). Der Zwischenspeicher ändert keine Zahl: gespeichert gleich ungespeichert (bitgleich),
ein anderer Parameter kommt nie aus dem Speicher, ein zweiter Aufruf mit denselben Parametern rechnet nicht noch einmal."""

import kum_algorithm as A
import kum_constants as C
import kum_evaluation as ev
import kum_live as L
from kum_scenario import make_instanz
from streamlit.testing.v1 import AppTest


def _zaehler(monkeypatch):
    """Zählt die Aufrufe von `A.loese` (die einzige teure Rechnung der Einheiten)."""
    aufrufe = []
    echt = A.loese

    def zaehlend(*args, **kwargs):
        aufrufe.append((args[1], kwargs.get("budget", args[2] if len(args) > 2 else None)))
        return echt(*args, **kwargs)

    monkeypatch.setattr(A, "loese", zaehlend)
    return aufrufe


def _gleich(a, b):
    return (a.optimum, a.bewiesen, a.z.als_dict(), a.plan) == (b.optimum, b.bewiesen, b.z.als_dict(), b.plan)


def test_stufe_lauf_gespeichert_gleich_ungespeichert_und_gleich_live_vergleich():
    L.stufe_lauf.clear()
    key = (3, 8, 1, 3, 400)
    ref = ev.live_vergleich(ev.Settings(seed=3, n=8, res=1, cap=3, budget=400))
    for s in C.STAGES:
        roh = L.stufe_lauf_ungespeichert(*key, s)
        erster, zweiter = L.stufe_lauf(*key, s), L.stufe_lauf(*key, s)
        assert _gleich(roh, ref[s]) and _gleich(erster, roh) and _gleich(zweiter, roh), s


def test_stufe_lauf_zweiter_aufruf_rechnet_nicht_anderer_parameter_schon(monkeypatch):
    L.stufe_lauf.clear()
    aufrufe = _zaehler(monkeypatch)
    L.stufe_lauf(3, 8, 1, 3, 400, 1)
    L.stufe_lauf(3, 8, 1, 3, 400, 1)
    assert len(aufrufe) == 1
    a = L.stufe_lauf(4, 8, 1, 3, 400, 1)            # anderer Zufalls-Seed
    b = L.stufe_lauf(3, 8, 1, 3, 400, 2)            # andere Stufe
    c = L.stufe_lauf(3, 8, 1, 3, 200, 1)            # anderes Budget
    assert len(aufrufe) == 4
    assert _gleich(a, L.stufe_lauf_ungespeichert(4, 8, 1, 3, 400, 1)) and _gleich(b, L.stufe_lauf_ungespeichert(3, 8, 1, 3, 400, 2))
    assert _gleich(c, L.stufe_lauf_ungespeichert(3, 8, 1, 3, 200, 1))


def _alte_reihe(zelle, budget, stufen=C.STAGES):
    """Die Messreihe so, wie sie vor dem Zwischenspeicher gerechnet wurde (unabhängige Abschrift der früheren Fassung)."""
    n, res, cap = C.ZELLEN[zelle]
    zeilen = []
    for seed in C.SWEEP_SEEDS:
        inst = make_instanz(n, res, cap, seed)
        zeilen.append({"seed": seed, "stufen": {str(st): {**{"optimum": r.optimum, "bewiesen": r.bewiesen}, **r.z.als_dict()} for st in stufen for r in [A.loese(inst, st, budget=budget)]}})
    return {"n": n, "ressourcen": res, "kap": cap, "seeds": list(C.SWEEP_SEEDS), "budget": budget, "stufen": list(stufen), "instanzen": zeilen}


def test_reihe_aus_einheiten_bitgleich_zur_alten_reihe():
    L.reihe_einheit.clear()
    alt = _alte_reihe("A", 300)
    assert ev.live_reihe("A", 300) == alt
    assert ev.live_reihe_aufbauen("A", 300, L.reihe_einheit) == alt
    assert ev.live_reihe_aufbauen("A", 300, L.reihe_einheit) == alt       # zweiter Durchlauf aus dem Speicher


def test_reihe_einheit_anderer_parameter_kommt_nicht_aus_dem_speicher(monkeypatch):
    L.reihe_einheit.clear()
    aufrufe = _zaehler(monkeypatch)
    e1 = L.reihe_einheit("A", 0, 1, 300)
    L.reihe_einheit("A", 0, 1, 300)
    assert len(aufrufe) == 1
    e2 = L.reihe_einheit("A", 0, 1, 301)
    e3 = L.reihe_einheit("A", 1, 1, 300)
    assert len(aufrufe) == 3
    assert e1 == ev.live_reihe_einheit("A", 0, 1, 300) and e2 == ev.live_reihe_einheit("A", 0, 1, 301) and e3 == ev.live_reihe_einheit("A", 1, 1, 300)


def test_fortschrittsanzeige_liefert_ergebnisse_in_reihenfolge_und_ohne_fehler():
    def skript():
        import streamlit as st
        import kum_live as L

        erg = L.mit_fortschritt("Probe", [("eins", (1,)), ("zwei", (2,)), ("drei", (3,))], lambda x: x * 10)
        st.write(f"ergebnis {erg}")

    at = AppTest.from_function(skript)
    at.run(timeout=60)
    assert not at.exception, [str(e) for e in at.exception]
    assert any("ergebnis [10, 20, 30]" in m.value for m in at.markdown)
