"""Verdikte an von Hand gesetzten Werten (DEMO-PLAYBOOK §12): jede Zahl im Text und jede Schwelle der Art steht hier.

Ein Verdikt ist eine reine Funktion (Art, Text) und bekommt Zeilen, nicht Seeds."""

import pytest

import kum_algorithm as A
import kum_constants as C
import kum_evaluation as ev
from kum_scenario import H1, H2


def _row(stufe, median, p90, maximum, bewiesen, n=10):
    return {"stufe": stufe, "n": n, "median": median, "p90": p90, "max": maximum, "bewiesen": bewiesen, "abbrueche": n - bewiesen, "summe": 0, "luecke_median": None, "luecke_max": None}


def _paar(beide=5, median=0.0, maximum=0.1, mit=2, gleich=3, mehr=0, n=10):
    return {"n": n, "beide": beide, "median": median, "max": maximum, "mit_ersparnis": mit, "gleich": gleich, "mehr_bewiesen": mehr, "weniger_bewiesen": 0}


def test_verdict_pflichtteile_schluesse_fehlschlag_und_nichts():
    kind, text = ev.verdict_pflichtteile(A.fixpunkt(H1, 7, 1), "H1", 7, 1, 15)
    assert kind == "info" and "2 Timetabling-Schlüsse verkleinern die Summe der Fensterbreiten von 15 auf 13" in text and "kein Fehlschlag" in text
    kind, text = ev.verdict_pflichtteile(A.fixpunkt(H1, 6, 1), "H1", 6, 1, 10)
    assert kind == "success" and "Fehlschlag an der Wurzel" in text and "keinen Plan mit Makespan höchstens 6" in text and "R: kein Startzeitpunkt im Fenster [1, 3]" in text
    kind, text = ev.verdict_pflichtteile(A.fixpunkt(H2, 8, 1), "H2", 8, 1, 24)
    assert kind == "info" and "ohne verschobene Fenstergrenze (Summe der Fensterbreiten 24" in text
    kind, text = ev.verdict_pflichtteile(A.fixpunkt(H2, 7, 2), "H2", 7, 2, 19)
    assert kind == "success" and "Energie P: 4·1" in text and "15 > Kapazität 2 · Länge 7 = 14" in text


def test_verdict_stufen_nennt_beweise_median_und_tail():
    rows = [_row(0, 3063, 20001, 20001, 7), _row(1, 50, 6781, 6781, 10), _row(2, 50, 5765, 5765, 10)]
    kind, text = ev.verdict_stufen(rows, "Zelle A")
    assert kind == "success"
    assert "Zelle A (10 feste Instanzen): Timetabling beweist das Optimum in 10 von 10 Instanzen im Knotenbudget, reine Vorrang-Verzweigung in 7." in text
    assert "Median der Knoten: 3.063 gegen 50 (61,3-fach weniger); 90-%-Wert 20.001 gegen 6.781, Maximum 20.001 gegen 6.781." in text
    assert "3 Läufe brachen am Knotenbudget ab" in text


def test_verdict_stufen_schwelle_faktor_2_ist_inklusive_und_gleich_viele_beweise():
    gleich = [_row(0, 80, 1, 1, 10), _row(1, 40, 1, 1, 10)]
    assert ev.verdict_stufen(gleich, "x")[0] == "success"                                       # genau Faktor 2
    assert ev.verdict_stufen([_row(0, 79, 1, 1, 10), _row(1, 40, 1, 1, 10)], "x")[0] == "info"  # Faktor 1,975
    kind, text = ev.verdict_stufen([_row(0, 20001, 20001, 20001, 1), _row(1, 15123, 20001, 20001, 5)], "x")
    assert kind == "success" and "5 von 10" in text and "in 1." in text                          # mehr Beweise genügen auch ohne Faktor 2
    assert "brachen" in text and "(1,3-fach weniger)" in text
    kind, text = ev.verdict_stufen([_row(0, 0, 0, 0, 10), _row(1, 0, 0, 0, 10)], "x")           # Nenner 0: kein Faktor
    assert kind == "info" and "fach weniger" not in text and "brachen" not in text


def test_verdict_energie_kaum_wirkung_schwelle_und_zusatzbeweis():
    rows = [_row(1, 50, 1, 1, 10), _row(2, 50, 1, 1, 10)]
    kind, text = ev.verdict_energie(_paar(beide=10, median=0.0, maximum=0.15, mit=4, gleich=6), rows, "Zelle A")
    assert kind == "info" and "Stufe 2 beweist 10 von 10 Instanzen, Stufe 1 10." in text
    assert "Unter den 10 Instanzen, die beide beweisen, spart die Energieprüfung im Median 0 % der Knoten (Maximum 15 %; in 4 dieser Instanzen überhaupt etwas, in 6 genau gleich viele Knoten)." in text
    assert "Das ist kaum Wirkung (Schwelle: Median unter 20 % und keine zusätzlich bewiesene Instanz)" in text and "nicht für Edge-Finding" in text
    # genau auf der Schwelle: nicht mehr „kaum“
    kind, text = ev.verdict_energie(_paar(median=0.2), rows, "x")
    assert kind == "success" and "bei oder über der Schwelle von 20 %" in text
    assert ev.verdict_energie(_paar(median=0.19), rows, "x")[0] == "info"
    # eine zusätzlich bewiesene Instanz hebt das Urteil „kaum Wirkung“ auf
    rows2 = [_row(1, 50, 1, 1, 5), _row(2, 50, 1, 1, 6)]
    kind, text = ev.verdict_energie(_paar(median=0.0, mehr=1), rows2, "x")
    assert kind == "success" and "Sie beweist 1 Instanz mehr als Stufe 1." in text and "kaum Wirkung" not in text
    assert "2 Instanzen mehr" not in text and "Sie beweist 2 Instanzen mehr" in ev.verdict_energie(_paar(mehr=2), rows2, "x")[1]
    # keine gemeinsam bewiesene Instanz: keine Ersparnis bestimmbar
    kind, text = ev.verdict_energie(_paar(beide=0, median=None, maximum=None, mit=0, gleich=0), rows, "x")
    assert kind == "info" and "lässt sich deshalb nicht bestimmen" in text


def test_schwelle_kaum_wirkung_ist_20_prozent():
    assert C.SCHWELLE_KAUM_WIRKUNG == 0.20


def test_verdict_groesse_nennt_faktoren():
    zeilen = [{"zelle": "A", "n": 10, "H": 36, "variablen": 1000, "klauseln": 4000, "instanzen": 10}, {"zelle": "B", "n": 15, "H": 52, "variablen": 2000, "klauseln": 10000, "instanzen": 10},
              {"zelle": "C", "n": 20, "H": 60, "variablen": 6000, "klauseln": 30000, "instanzen": 10}]
    kind, text = ev.verdict_groesse(zeilen)
    assert kind == "info" and "Median über 10 Instanzen je Zelle" in text and "Zelle A (n = 10): 1.000 Variablen, 4.000 Klauseln (H im Median 36)" in text
    assert "Klauseln je Größenstufe: ×2,5, ×3,0." in text and "nicht getrennt gemessen" in text


def test_verdict_sat_nennt_mediane_verhaeltnis_und_ursache_nicht_getrennt():
    st = {"n": 6, "sat_median": 200, "sat_max": 1800, "cpsat_median": 4, "cpsat_max": 200, "abbrueche": 0, "gleiche_antwort": 6, "variablen": 1, "klauseln": 1}
    kind, text = ev.verdict_sat({"A_opt": st, "A_opt1": {**st, "cpsat_median": 0, "abbrueche": 1, "gleiche_antwort": 5}})
    assert kind == "info" and "Zelle A, H = Optimum (erfüllbar): Kern-CDCL 200 Konflikte im Median (Maximum 1.800), CP-SAT 4 (Maximum 200), Verhältnis der Mediane 50,0" in text
    assert "Zelle A, H = Optimum − 1 (unerfüllbar): Kern-CDCL 200 Konflikte im Median (Maximum 1.800), CP-SAT 0 (Maximum 200), 1 Abbrüche am Budget" in text     # Nenner 0: kein Verhältnis
    assert "Verhältnis der Mediane" not in text.split("Optimum − 1")[1]
    assert "stimmt mit CP-SAT in 11 von 12 Läufen überein" in text and "nicht getrennt gemessen" in text


def _ergebnis(opt, bewiesen, knoten):
    return A.Ergebnis(opt, bewiesen, None, opt, A.Zaehler(knoten=knoten))


def test_verdict_einzel():
    kind, text = ev.verdict_einzel({0: _ergebnis(30, True, 6277), 1: _ergebnis(30, True, 459), 2: _ergebnis(30, True, 459)}, 20000)
    assert kind == "info" and "Optimaler Makespan 30, bewiesen von 3 der 3 Stufen." in text and "Stufe 0: 6.277 Knoten" in text and "Stufe 0 braucht hier 13,7-mal so viele Knoten wie Stufe 1." in text
    assert "Die Energieprüfung spart auf dieser Instanz nichts." in text and "Einzelinstanz, kein Median." in text
    kind, text = ev.verdict_einzel({0: _ergebnis(40, False, 20001), 1: _ergebnis(39, False, 20001), 2: _ergebnis(39, False, 20001)}, 20000)
    assert "Keine Stufe beweist das Optimum innerhalb von 20.000 Knoten; der beste gefundene Makespan ist 39." in text and "Abbruch am Budget" in text and "braucht hier" not in text
    assert ev.verdict_einzel({0: _ergebnis(30, True, 1), 1: _ergebnis(31, True, 1)}, 10)[0] == "error"
    assert "keinen Plan" in ev.verdict_einzel({0: _ergebnis(None, True, 0), 1: _ergebnis(None, True, 0)}, 10)[1]


def test_verdict_sat_live():
    class Sat:
        def __init__(self, antwort, konflikte=12, variablen=1000, klauseln=5000):
            self.antwort, self.konflikte, self.variablen, self.klauseln = antwort, konflikte, variablen, klauseln

    mini = A.Entscheidung(False, None, A.Zaehler(knoten=3))
    kind, text = ev.verdict_sat_live(Sat(False), 29, mini, 5000)
    assert kind == "success" and "beweist: kein Plan mit Makespan höchstens 29 nach 12 Konflikten (1.000 Variablen, 5.000 Klauseln)" in text and "Mini-CP (Stufe 1) gibt dieselbe Antwort (3 Knoten)" in text
    kind, text = ev.verdict_sat_live(Sat(True), 29, mini, 5000)
    assert kind == "error" and "Widerspruch" in text
    kind, text = ev.verdict_sat_live(Sat(None, 5000), 29, mini, 5000)
    assert kind == "warning" and "nach 5.000 Konflikten (Budget 5.000) ab" in text
    kind, text = ev.verdict_sat_live(Sat(True), 29, A.Entscheidung(None, None, A.Zaehler(knoten=20001)), 5000)
    assert kind == "info" and "kein Vergleich möglich" in text and "findet einen Plan mit Makespan höchstens 29" in text


def test_statistik_und_paar_ersparnis_an_handreihe():
    def st(knoten, bew, opt=10):
        return {"optimum": opt, "bewiesen": bew, "knoten": knoten}

    reihe = {"stufen": [1, 2], "instanzen": [
        {"seed": 0, "cpsat": {"optimum": 10, "bewiesen": True}, "stufen": {"1": st(100, True), "2": st(50, True)}},      # 50 % Ersparnis
        {"seed": 1, "cpsat": {"optimum": 10, "bewiesen": True}, "stufen": {"1": st(40, True), "2": st(40, True)}},       # gleich
        {"seed": 2, "cpsat": {"optimum": 10, "bewiesen": True}, "stufen": {"1": st(0, True), "2": st(0, True)}},         # Nenner 0: Ersparnis 0
        {"seed": 3, "cpsat": {"optimum": 9, "bewiesen": True}, "stufen": {"1": st(20001, False, 10), "2": st(500, True, 9)}},   # nur Stufe 2 beweist
        {"seed": 4, "cpsat": {"optimum": 9, "bewiesen": False}, "stufen": {"1": st(20001, False, 10), "2": st(20001, False, 10)}},
    ]}
    p = ev.paar_ersparnis(reihe)
    assert (p["n"], p["beide"], p["median"], p["max"], p["mit_ersparnis"], p["gleich"], p["mehr_bewiesen"], p["weniger_bewiesen"]) == (5, 3, 0.0, 0.5, 1, 2, 1, 0)
    r1, r2 = ev.statistik(reihe)
    assert (r1["bewiesen"], r1["abbrueche"], r1["median"], r1["max"]) == (3, 2, 100, 20001) and r2["bewiesen"] == 4
    assert r1["luecke_median"] == 0 and r1["luecke_max"] == 1 and r2["luecke_max"] == 0         # Lücken nur über Instanzen mit bewiesenem CP-SAT-Optimum (vier)
    assert ev.optima_stimmen(reihe) == (7, 7) and ev.nie_unter_cpsat(reihe)
    assert ev.p90([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == 9 and ev.p90([5]) == 5


def test_zahlenformat():
    assert ev._zahl(20001) == "20.001" and ev._zahl(152.5) == "152,5" and ev._zahl(7.0) == "7" and ev._zahl(0) == "0"


@pytest.mark.parametrize("wert", [0.0, 0.5, 1.0])
def test_prozentformat(wert):
    assert ev._prozent(wert) == f"{round(100 * wert)} %"
