"""Die vorgerechneten Messreihen (`kum_sweeps.json`, Messskript tools/messung_sweeps.py) gegen eine Neuberechnung und gegen CP-SAT.

Im Repo wird der kleinere Teil nachgerechnet (Zelle A alle Stufen, B und C die Läufe mit höchstens 3.000 Knoten, die Größen der Zellen A bis C gebaut und D gezählt, die SAT-Läufe mit höchstens 300
Konflikten); die großen Läufe, die CP-SAT-Zahlen und die langen SAT-Läufe stehen nur im Messskript. CP-SAT-Zahlen hängen an der OR-Tools-Version (`meta`)."""

import pytest

import kum_algorithm as A
import kum_constants as C
import kum_evaluation as ev
import kum_sat as S
from kum_scenario import beste_konstruktion, make_instanz, untere_schranke

DATA = ev.lade_sweeps()


def test_meta_nennt_skript_und_versionen():
    meta = DATA["meta"]
    assert meta["skript"] == C.MEASURE_SCRIPT and meta["ortools"] and meta["python"] and meta["datum"]


def test_die_seeds_und_budgets_der_reihen_sind_die_der_konstanten():
    for key, reihe in DATA["reihen"].items():
        assert reihe["seeds"] == list(C.SWEEP_SEEDS) and reihe["budget"] == C.SWEEP_BUDGET and reihe["stufen"] == list(C.STAGES)
        assert (reihe["n"], reihe["ressourcen"], reihe["kap"]) == C.ZELLEN[key]
    assert set(DATA["reihen"]) == {"A", "B", "C"} and set(DATA["groesse"]) == {"A", "B", "C", "D"}
    for key, s in DATA["sat"].items():
        assert s["budget"] == C.SAT_BUDGET and s["seeds"] == list(C.SAT_SEEDS)


def test_zelle_a_alle_stufen_stimmen_mit_der_neuberechnung_ueberein():
    reihe = DATA["reihen"]["A"]
    for z in reihe["instanzen"]:
        inst = make_instanz(10, 1, 3, z["seed"])
        assert z["untere_schranke"] == untere_schranke(inst) and z["start_schranke"] == beste_konstruktion(inst)[0]
        for s in C.STAGES:
            r = A.loese(inst, s, budget=reihe["budget"])
            e = z["stufen"][str(s)]
            assert (r.z.knoten, r.z.fehlschlaege, r.optimum, r.bewiesen) == (e["knoten"], e["fehlschlaege"], e["optimum"], e["bewiesen"]), (z["seed"], s)


@pytest.mark.parametrize("key", ["B", "C"])
def test_zellen_b_und_c_laeufe_bis_3000_knoten_stimmen_ueberein(key):
    reihe = DATA["reihen"][key]
    n, res, cap = C.ZELLEN[key]
    geprueft = 0
    for z in reihe["instanzen"]:
        inst = make_instanz(n, res, cap, z["seed"])
        for s in C.STAGES:
            e = z["stufen"][str(s)]
            if e["knoten"] <= 3000:
                r = A.loese(inst, s, budget=reihe["budget"])
                assert (r.z.knoten, r.optimum, r.bewiesen) == (e["knoten"], e["optimum"], e["bewiesen"]), (key, z["seed"], s)
                geprueft += 1
    assert geprueft >= 1


def test_alle_bewiesenen_optima_stimmen_mit_cpsat_ueberein_und_kein_wert_liegt_darunter():
    for key, reihe in DATA["reihen"].items():
        ok, gesamt = ev.optima_stimmen(reihe)
        assert ok == gesamt > 0, key
        assert ev.nie_unter_cpsat(reihe), key


def test_cpsat_optimum_der_zelle_a_gegen_neuberechnung():
    pytest.importorskip("ortools")
    from orakel import cpsat_optimum

    for z in DATA["reihen"]["A"]["instanzen"][:4]:
        opt, bewiesen = cpsat_optimum(make_instanz(10, 1, 3, z["seed"]))
        assert bewiesen and opt == z["cpsat"]["optimum"] and z["cpsat"]["bewiesen"]


def test_groessen_stimmen_mit_der_neuberechnung_ueberein():
    for key, g in DATA["groesse"].items():
        n, res, cap = C.ZELLEN[key]
        assert (g["n"], g["ressourcen"], g["kap"]) == (n, res, cap) and g["seeds"] == list(C.SWEEP_SEEDS)
        for z in g["instanzen"][: 10 if key != "C" else 5]:
            inst = make_instanz(n, res, cap, z["seed"])
            H = beste_konstruktion(inst)[0]
            assert z["H"] == H and (z["variablen"], z["klauseln"]) == S.groesse(inst, H), (key, z["seed"])
    for z in DATA["groesse"]["A"]["instanzen"][:3]:                      # gebaute Kodierung gegen die gezählte Größe
        kod = S.kodiere(make_instanz(10, 1, 3, z["seed"]), z["H"])
        assert (kod.n_variablen, len(kod.klauseln)) == (z["variablen"], z["klauseln"])


def test_sat_laeufe_bis_300_konflikte_stimmen_ueberein_und_alle_antworten_gleichen_cpsat():
    geprueft = 0
    for key, s in DATA["sat"].items():
        n, res, cap = C.ZELLEN[s["zelle"]]
        for z in s["instanzen"]:
            assert z["cpsat_antwort"] == (s["fall"] == "opt") and z["sat_antwort"] in (None, z["cpsat_antwort"]), (key, z["seed"])      # keine falsche Antwort, höchstens ein Abbruch
            if z["sat_konflikte"] <= 300:
                r = S.sat_entscheide(make_instanz(n, res, cap, z["seed"]), z["H"], s["budget"])
                assert (r.antwort, r.konflikte, r.variablen, r.klauseln) == (z["sat_antwort"], z["sat_konflikte"], z["variablen"], z["klauseln"]), (key, z["seed"])
                geprueft += 1
    assert geprueft >= 3
