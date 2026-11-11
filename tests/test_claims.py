"""Jede Zahl der README in einem Test (DEMO-PLAYBOOK §4 und §11a): über dieselben Auswertungsfunktionen wie in der App, auf den festen Instanzen der Messreihen (`kum_sweeps.json`).

Die JSON-Datei selbst ist in `tests/test_sweeps.py` gegen eine Neuberechnung geprüft (Zelle A alle Stufen, B und C die kleinen Läufe, Größen, kurze SAT-Läufe); hier stehen die Zählungen, die der Text nennt.
Nicht im Test, sondern Messung der README: die CP-SAT-Zahlen (hängen an der OR-Tools-Version, stehen in der JSON-Datei) und die langen SAT-Läufe (Messskript)."""

import kum_algorithm as A
import kum_aufzaehlung as Z
import kum_constants as C
import kum_evaluation as ev
from kum_scenario import H1, H2, make_instanz

DATA = ev.lade_sweeps()
R = DATA["reihen"]


def _stat(key):
    return {r["stufe"]: r for r in ev.statistik(R[key])}


def test_claim_handbeispiele():
    a1, a2 = Z.aufzaehlen(H1), Z.aufzaehlen(H2)
    assert (a1.optimum, a1.am_optimum, a1.unter_optimum) == (7, 24, 0) and (a2.optimum, a2.am_optimum, a2.unter_optimum) == (8, 12, 0)
    f0, f1 = A.fixpunkt(H1, 7, 0), A.fixpunkt(H1, 7, 1)
    assert (A.fensterbreite(f0.est, f0.lst), A.fensterbreite(f1.est, f1.lst)) == (15, 13)
    assert (f1.est, f1.lst) == ([0, 0, 0, 1, 4], [3, 3, 2, 4, 6]) and A.pflichtprofil(H1, f0.est, f0.lst, 7) == [0, 0, 0, 2, 0, 0, 0]
    assert not A.fixpunkt(H1, 6, 1).ok and A.fixpunkt(H1, 6, 0).ok
    assert A.fixpunkt(H2, 7, 1).ok and not A.fixpunkt(H2, 7, 2).ok and 4 + 4 + 1 + 2 + 4 == 15 > 2 * 7
    assert A.fensterbreite(*(lambda f: (f.est, f.lst))(A.fixpunkt(H2, 8, 1))) == 24


def test_claim_knoten_der_handbeispiele():
    erwartet = {(1, 7): (18, 4, 4), (1, 6): (95, 1, 1), (2, 8): (22, 7, 7), (2, 7): (91, 3, 1)}
    for (bsp, H), knoten in erwartet.items():
        inst = H1 if bsp == 1 else H2
        assert tuple(A.entscheide(inst, H, s).z.knoten for s in (0, 1, 2)) == knoten


def test_claim_timetabling_gegen_vorrang_je_zelle():
    s = {k: _stat(k) for k in "ABC"}
    assert [(s["A"][i]["bewiesen"]) for i in (0, 1, 2)] == [7, 9, 9] and [(s["B"][i]["bewiesen"]) for i in (0, 1, 2)] == [1, 3, 4] and [(s["C"][i]["bewiesen"]) for i in (0, 1, 2)] == [0, 2, 2]
    assert [s["A"][i]["median"] for i in (0, 1, 2)] == [5354, 452, 450] and round(5354 / 452, 1) == 11.8
    assert [s["A"][i]["p90"] for i in (0, 1, 2)] == [20001, 2299, 2217] and [s["A"][i]["max"] for i in (0, 1, 2)] == [20001, 20001, 20001]
    assert all(s[k][i]["median"] == 20001 for k in "BC" for i in (0, 1, 2))                       # Median am Budget: untere Schranke
    assert [s["A"][i]["abbrueche"] for i in (0, 1, 2)] == [3, 1, 1] and [s["B"][i]["abbrueche"] for i in (0, 1, 2)] == [9, 7, 6] and [s["C"][i]["abbrueche"] for i in (0, 1, 2)] == [10, 8, 8]
    assert [s["B"][i]["summe"] for i in (0, 1, 2)] == [180009, 149707, 146767] and [s["C"][i]["summe"] for i in (0, 1, 2)] == [200010, 182542, 181196]


def test_claim_luecke_zum_optimum_bei_abbruch():
    s = {k: _stat(k) for k in "ABC"}
    assert [(s["B"][i]["luecke_median"], s["B"][i]["luecke_max"]) for i in (0, 1, 2)] == [(1, 4), (0, 1), (0, 1)]
    assert [(s["C"][i]["luecke_median"], s["C"][i]["luecke_max"]) for i in (0, 1, 2)] == [(4, 8), (1, 3), (1, 3)]
    assert [(s["A"][i]["luecke_median"], s["A"][i]["luecke_max"]) for i in (0, 1, 2)] == [(0, 2), (0, 1), (0, 0)]


def test_claim_energie_je_zelle():
    p = {k: ev.paar_ersparnis(R[k]) for k in "ABC"}
    assert (p["A"]["beide"], round(100 * p["A"]["median"], 1), round(100 * p["A"]["max"]), p["A"]["mit_ersparnis"], p["A"]["gleich"], p["A"]["mehr_bewiesen"]) == (9, 0.9, 73, 5, 4, 0)
    assert (p["B"]["beide"], round(100 * p["B"]["median"]), round(100 * p["B"]["max"]), p["B"]["mit_ersparnis"], p["B"]["gleich"], p["B"]["mehr_bewiesen"]) == (3, 13, 53, 2, 1, 1)
    assert (p["C"]["beide"], round(100 * p["C"]["median"]), round(100 * p["C"]["max"]), p["C"]["mit_ersparnis"], p["C"]["gleich"], p["C"]["mehr_bewiesen"]) == (2, 8, 10, 2, 0, 0)
    assert all(p[k]["weniger_bewiesen"] == 0 for k in "ABC")
    kinds = {k: ev.verdict_energie(p[k], ev.statistik(R[k]), k)[0] for k in "ABC"}
    assert kinds == {"A": "info", "B": "success", "C": "info"}                                      # kaum Wirkung in A und C, eine Instanz mehr in B


def test_claim_nullknoten_instanzen():
    """Zelle A und B, Zufalls-Seed 4: die untere Schranke gleicht der Startschranke, kein Suchknoten nötig (in allen drei Stufen)."""
    for key in "AB":
        z = R[key]["instanzen"][4]
        assert z["seed"] == 4 and z["untere_schranke"] == z["start_schranke"] and all(st["knoten"] == 0 and st["bewiesen"] for st in z["stufen"].values())
        assert [i["seed"] for i in R[key]["instanzen"] if i["stufen"]["1"]["knoten"] == 0] == [4]
    assert not [i for i in R["C"]["instanzen"] if i["stufen"]["1"]["knoten"] == 0]


def test_claim_cpsat_gegenprobe():
    cp = {k: ev.cpsat_stat(R[k]) for k in "ABC"}
    assert (cp["A"]["bewiesen"], cp["A"]["median"], cp["A"]["max"]) == (10, 81.5, 6033)
    assert (cp["B"]["bewiesen"], cp["B"]["median"], cp["B"]["max"]) == (9, 8560.5, 657837)
    assert (cp["C"]["bewiesen"], cp["C"]["median"], cp["C"]["max"]) == (9, 6832, 928580)
    assert [ev.optima_stimmen(R[k]) for k in "ABC"] == [(25, 25), (8, 8), (4, 4)] and all(ev.nie_unter_cpsat(R[k]) for k in "ABC")


def test_claim_groesse():
    g = {z["zelle"]: z for z in ev.groesse_statistik(DATA["groesse"])}
    assert (g["A"]["H"], g["A"]["variablen"], g["A"]["klauseln"]) == (34, 6141.5, 20804.5)
    assert (g["B"]["H"], g["B"]["variablen"], g["B"]["klauseln"]) == (51.5, 26625, 98063.5)
    assert (g["C"]["H"], g["C"]["variablen"], g["C"]["klauseln"]) == (57, 43069, 158784.5)
    assert (g["D"]["H"], g["D"]["variablen"], g["D"]["klauseln"]) == (90, 184978.5, 740661.5)
    f = [g[b]["klauseln"] / g[a]["klauseln"] for a, b in (("A", "B"), ("B", "C"), ("C", "D"))]
    assert [round(x, 1) for x in f] == [4.7, 1.6, 4.7]


def test_claim_presets_und_parameter():
    assert C.SWEEP_SEEDS == tuple(range(10)) and C.SWEEP_BUDGET == 20000 and C.LIVE_REIHE_BUDGET == 5000 and C.SCHWELLE_KAUM_WIRKUNG == 0.2
    assert make_instanz(10, 1, 3, 3) == make_instanz(10, 1, 3, 3)


def test_claim_sat_konflikte():
    s = {k: ev.sat_statistik(v) for k, v in DATA["sat"].items()}
    assert (s["A_opt"]["sat_median"], s["A_opt"]["sat_max"], s["A_opt"]["cpsat_median"], s["A_opt"]["cpsat_max"]) == (82, 651, 2.5, 62)
    assert (s["A_opt1"]["sat_median"], s["A_opt1"]["sat_max"], s["A_opt1"]["cpsat_median"], s["A_opt1"]["cpsat_max"]) == (3453, 20000, 122, 1606)
    assert (s["B_opt"]["sat_median"], s["B_opt"]["sat_max"], s["B_opt"]["cpsat_median"], s["B_opt"]["cpsat_max"]) == (2327, 17904, 403.5, 2160)
    assert [round(s[k]["sat_median"] / s[k]["cpsat_median"], 1) for k in ("A_opt", "A_opt1", "B_opt")] == [32.8, 28.3, 5.8]
    assert [s[k]["abbrueche"] for k in ("A_opt", "A_opt1", "B_opt")] == [0, 1, 0] and [s[k]["gleiche_antwort"] for k in ("A_opt", "A_opt1", "B_opt")] == [6, 5, 6]
    assert [(s[k]["variablen"], s[k]["klauseln"]) for k in ("A_opt", "A_opt1", "B_opt")] == [(6986, 23717), (6701, 22634.5), (23923.5, 86802.5)]
    assert all(x["n"] == 6 for x in s.values()) and sum(x["gleiche_antwort"] for x in s.values()) == 17


def test_claim_sat_abbruch_ist_der_einzige_und_sein_rest_ist_unerfuellbar():
    ab = [(k, z["seed"], z["H"]) for k, v in DATA["sat"].items() for z in v["instanzen"] if z["sat_antwort"] is None]
    assert ab == [("A_opt1", 1, 36)] and DATA["sat"]["A_opt1"]["instanzen"][1]["sat_konflikte"] == C.SAT_BUDGET
    assert all(z["sat_antwort"] is False for z in DATA["sat"]["A_opt1"]["instanzen"] if z["sat_antwort"] is not None)
    b0 = DATA["sat"]["B_opt"]["instanzen"][0]
    assert b0["cpsat_konflikte"] > b0["sat_konflikte"]                                           # B, Zufalls-Seed 0: CP-SAT braucht hier mehr Konflikte als das Kern-CDCL
