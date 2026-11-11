"""Jede Einheit an den Handbeispielen H1 und H2 gegen die Handrechnung (DEMO-PLAYBOOK §1b; Sollwerte aus sat-cp-planung/handbeispiele/hb_14.py, unabhängig mit reinem Python nachgerechnet).

Kapazität 2, eine Ressource, Aktivität (Dauer d, Bedarf r): H1 = P(4,1) Q(4,1) U(1,1) R(2,1) T(1,1) mit Vorrang U → R → T; H2 = P(4,1) Q(4,1) U(1,1) R(2,1) T(2,2) mit Vorrang U → R.
Indizes: P 0, Q 1, U 2, R 3, T 4."""

import pytest

import kum_algorithm as A
import kum_scenario as Sc
from kum_scenario import H1, H2, Instanz, make_instanz


# ------------------------------------------------------------------------------------------------------------------------------ Szenario
def test_schranken_von_hand():
    """H1: längste Kette U, R, T = 1 + 2 + 1 = 4; Energie (4 + 4 + 1 + 2 + 1) / 2 = 6; H2: Kette 4 (die längste Aktivität P; U, R sind 3), Energie (4 + 4 + 1 + 2 + 4) / 2 = 7,5, aufgerundet 8."""
    assert Sc.fruehester_start(H1) == [0, 0, 0, 1, 3] and Sc.kettenlaenge(H1) == 4
    assert (Sc.energie_schranke(H1), Sc.untere_schranke(H1)) == (6, 6)
    assert (Sc.kettenlaenge(H2), Sc.energie_schranke(H2), Sc.untere_schranke(H2)) == (4, 8, 8)


def test_planpruefer_von_hand():
    """Plan (P, Q, U, R, T) = (0, 3, 0, 1, 4) hat Makespan 7 und ist zulässig; die Fehlerfälle werden benannt."""
    assert Sc.pruefe_plan(H1, (0, 3, 0, 1, 4)) == (True, "") and Sc.makespan(H1, (0, 3, 0, 1, 4)) == 7
    ok, grund = Sc.pruefe_plan(H1, (0, 0, 0, 1, 4))                    # im Zeitpunkt 0 laufen P, Q, U: Bedarf 3 > 2
    assert not ok and "Zeitpunkt 0" in grund and "Bedarf 3" in grund
    ok, grund = Sc.pruefe_plan(H1, (0, 3, 1, 1, 4))                    # U endet in 2, R startet in 1
    assert not ok and "Vorrang U vor R" in grund
    assert not Sc.pruefe_plan(H1, (0, 3, 0, 1, -1))[0] and not Sc.pruefe_plan(H1, (0, 3, 0))[0]


def test_erzeuger_ist_deterministisch_und_haelt_seine_bereiche():
    a, b = make_instanz(10, 1, 3, 7), make_instanz(10, 1, 3, 7)
    assert a == b and a != make_instanz(10, 1, 3, 8)
    for seed in range(20):
        inst = make_instanz(12, 2, 4, seed)
        assert all(1 <= d <= 9 for d in inst.d) and all(0 <= c <= 4 for z in inst.bedarf for c in z)
        assert all(any(inst.bedarf[r][i] for r in range(2)) for i in range(12))           # jede Aktivität braucht eine Ressource
        assert all(0 < j - i <= 6 for i, j in inst.kanten) and inst.zulaessig()


def test_erzeuger_referenzwert_seed_0():
    """Eingefrorener Regressionswert des SplitMix64-Erzeugers (kein Handwert): n = 6, eine Ressource, Kapazität 2, Zufalls-Seed 0."""
    inst = make_instanz(6, 1, 2, 0)
    assert inst.d == (6, 6, 9, 3, 9, 5) and inst.kap == (2,) and inst.n == 6 and inst.kanten == ((4, 5),)
    assert inst.bedarf == ((2, 1, 2, 2, 2, 2),)


def test_serielle_konstruktion_liefert_einen_zulaessigen_plan_nicht_unter_dem_optimum():
    for inst, opt in ((H1, 7), (H2, 8)):
        ms, plan = Sc.beste_konstruktion(inst)
        assert Sc.pruefe_plan(inst, plan) == (True, "") and ms == Sc.makespan(inst, plan) and ms >= opt
    assert Sc.beste_konstruktion(Instanz(d=(2,), bedarf=((3,),), kap=(2,), kanten=())) is None


# ------------------------------------------------------------------------------------------------------------------- Propagation (H1)
def _texte(f, art):
    return [e.text for e in f.protokoll.ereignisse if e.art == art]


def test_fenster_nur_aus_vorrang_und_pflichtprofil_h1():
    """H = 7: P [0, 3], Q [0, 3], U [0, 3], R [1, 4], T [3, 6]; Pflichtteile von P und Q = [3, 4): Profil [0, 0, 0, 2, 0, 0, 0]; Summe der Fensterbreiten 15."""
    f = A.fixpunkt(H1, 7, 0)
    assert f.ok and (f.est, f.lst) == ([0, 0, 0, 1, 3], [3, 3, 3, 4, 6])
    assert A.pflichtprofil(H1, f.est, f.lst, 7) == [0, 0, 0, 2, 0, 0, 0] and A.fensterbreite(f.est, f.lst) == 15
    assert [e.art for e in f.protokoll.ereignisse] == ["start", "fixpunkt"]                  # Stufe 0 schließt nichts


def test_timetabling_schluesse_h1():
    """U kann im Zeitpunkt 3 nicht laufen (Profil 2 + Bedarf 1 > 2): lst_U 3 → 2; T (Dauer 1) ebenso nicht: est_T 3 → 4. Fixpunkt = exakte Grenzen, Fensterbreiten 15 → 13."""
    f = A.fixpunkt(H1, 7, 1)
    assert f.ok and (f.est, f.lst) == ([0, 0, 0, 1, 4], [3, 3, 2, 4, 6]) and A.fensterbreite(f.est, f.lst) == 13
    assert _texte(f, "timetabling") == [
        "U kann im Zeitpunkt 3 nicht laufen: Profil 2 + Bedarf 1 > Kapazität 2, lst(U) 3 → 2",
        "T kann im Zeitpunkt 3 nicht laufen: Profil 2 + Bedarf 1 > Kapazität 2, est(T) 3 → 4",
    ]
    assert f.z.tt_schluesse == 2 and f.protokoll.ereignisse[-1].art == "fixpunkt"


def test_fehlschlag_bei_horizont_6_h1():
    """H = 6: P und Q haben die Pflichtteile [2, 4) (Profil [0, 0, 2, 2, 0, 0]); R mit Fenster [1, 3] hat keinen Startzeitpunkt, der die Zeitpunkte 2 und 3 meidet."""
    f = A.fixpunkt(H1, 6, 1)
    assert not f.ok and f.z.fehl_timetabling == 1
    assert A.pflichtprofil(H1, [0, 0, 0, 1, 3], [2, 2, 2, 3, 5], 6) == [0, 0, 2, 2, 0, 0]
    assert _texte(f, "fehlschlag") == ["R: kein Startzeitpunkt im Fenster [1, 3] mit Profil [0, 0, 2, 2, 0, 0] (Dauer 2, Bedarf 1, Kapazität 2) → Fehlschlag"]
    assert A.fixpunkt(H1, 6, 0).ok                                                           # reiner Vorrang sieht den Fehlschlag nicht


def test_horizont_8_h1_nichts_zu_schliessen():
    f = A.fixpunkt(H1, 8, 1)
    assert f.ok and f.z.tt_schluesse == 0 and A.pflichtprofil(H1, f.est, f.lst, 8) == [0] * 8


def test_zu_kurzer_horizont_macht_ein_fenster_leer():
    f = A.fixpunkt(H1, 3, 1)                                                                 # die Kette U, R, T braucht 4
    assert not f.ok and f.z.fehl_vorrang == 1 and f.protokoll.ereignisse[0].art == "start" and "Kette" in f.protokoll.ereignisse[0].text


# ------------------------------------------------------------------------------------------------------------------ Energie (H2)
def test_h2_timetabling_schliesst_nichts_energie_schlaegt_an():
    """H = 8: keine Aktivität hat einen Pflichtteil (Summe der Breiten 24 vorher und nachher). H = 7: Timetabling ohne Fehlschlag, Energie im Fenster [0, 7): 4 + 4 + 1 + 2 + 4 = 15 > 14."""
    f8 = A.fixpunkt(H2, 8, 1)
    assert f8.ok and A.fensterbreite(f8.est, f8.lst) == 24 == A.fensterbreite(*(A.fixpunkt(H2, 8, 0).est, A.fixpunkt(H2, 8, 0).lst))
    assert A.fixpunkt(H2, 7, 1).ok
    f7 = A.fixpunkt(H2, 7, 2)
    assert not f7.ok and f7.z.fehl_energie == 1 and f7.z.fehl_timetabling == 0
    assert _texte(f7, "fehlschlag") == ["Im Fenster [0, 7) brauchen die ganz hineinpassenden Aktivitäten die Energie P: 4·1 + Q: 4·1 + U: 1·1 + R: 2·1 + T: 2·2 = 15 > Kapazität 2 · Länge 7 = 14 → Fehlschlag"]


def test_energie_einheit_an_handfenstern():
    """Zwei Aktivitäten (Dauer 3, Bedarf 2, Kapazität 2) im Fenster [0, 5]: Energie 12 > 2 · 5 = 10; im Fenster [0, 6] genau 12 = 12: keine Überlast."""
    inst = Instanz(d=(3, 3), bedarf=((2, 2),), kap=(2,), kanten=())
    M = A.Modell(inst)
    assert A._energie(M, [0, 0], [2, 2]) == (0, 0, 5, 12, 10)
    assert A._energie(M, [0, 0], [3, 3]) is None


def test_stufe_0_prueft_nur_festgelegte_aktivitaeten():
    inst = Instanz(d=(3, 3), bedarf=((2, 2),), kap=(2,), kanten=())
    M = A.Modell(inst)
    assert A._fest_pruefung(M, [0, 0], [0, 1]) is None                  # nur die erste ist festgelegt
    assert A._fest_pruefung(M, [0, 1], [0, 1]) == (0, 1, 4)             # beide festgelegt und überlappend: Last 4 im Zeitpunkt 1
    assert A._fest_pruefung(M, [0, 3], [0, 3]) is None                  # hintereinander: in Ordnung


# -------------------------------------------------------------------------------------------------------------------------------- Suche
def test_entscheidungsfassung_h1_h2():
    """Antworten von Hand (hb_14.py): H1 bei 7 ja, bei 6 nein; H2 bei 8 ja, bei 7 nein. Wurzel-Fehlschläge: 1 Knoten."""
    for stufe in (0, 1, 2):
        assert A.entscheide(H1, 7, stufe).gefunden is True and A.entscheide(H1, 6, stufe).gefunden is False
        assert A.entscheide(H2, 8, stufe).gefunden is True and A.entscheide(H2, 7, stufe).gefunden is False
    assert (A.entscheide(H1, 6, 1).z.knoten, A.entscheide(H1, 6, 1).z.fehl_wurzel) == (1, 1)
    assert (A.entscheide(H2, 7, 2).z.knoten, A.entscheide(H2, 7, 2).z.fehl_energie) == (1, 1)
    assert A.entscheide(H2, 7, 1).z.knoten > 1                          # Timetabling allein braucht Suche


def test_knotenzahlen_der_handbeispiele_regressionswerte():
    """Eingefrorene Zählungen dieser Suche (kein Handwert): Knoten je Stufe 0 / 1 / 2."""
    erwartet = {(1, 7): (18, 4, 4), (1, 6): (95, 1, 1), (2, 8): (22, 7, 7), (2, 7): (91, 3, 1)}
    for (bsp, H), knoten in erwartet.items():
        inst = H1 if bsp == 1 else H2
        assert tuple(A.entscheide(inst, H, s).z.knoten for s in (0, 1, 2)) == knoten


def test_optimierung_findet_das_optimum_und_zaehlt_das_budget_mit():
    r = A.loese(H1, 1, 20000)
    assert r.optimum == 7 and r.bewiesen and Sc.pruefe_plan(H1, r.plan) == (True, "")
    assert A.loese(H2, 2, 20000).optimum == 8
    inst = make_instanz(15, 1, 4, 0)
    knapp = A.loese(inst, 1, 100)
    assert not knapp.bewiesen and knapp.z.knoten == 101 and knapp.optimum >= 1             # Abbruch zählt mit dem Budget (Budget + 1)


def test_iterative_suche_hat_kein_rekursionslimit():
    """Tiefe Suche bei großem Budget bricht nicht an der Rekursionsgrenze."""
    inst = make_instanz(20, 2, 4, 1)
    assert A.loese(inst, 0, 3000).z.knoten <= 3001


def test_paarwahl_nimmt_das_paar_mit_kleinster_spielraumsumme():
    """Drei Aktivitäten mit Bedarf 2 bei Kapazität 2: alle Paare stehen im Konflikt; die Wahl nimmt das Paar mit den engsten Fenstern, bei Gleichstand das kleinste Paar."""
    inst = Instanz(d=(2, 2, 2), bedarf=((2, 2, 2),), kap=(2,), kanten=())
    M = A.Modell(inst)
    reach = A._erreichbar(M, [])
    assert A._waehle_paar(M, [0, 0, 0], [4, 4, 4], reach) == (0, 1)                   # Gleichstand: kleinstes Paar
    assert A._waehle_paar(M, [0, 0, 0], [4, 1, 1], reach) == (1, 2)                   # Summe 2 gegen 5
    assert A._waehle_paar(M, [0, 3, 6], [0, 3, 6], reach) is None                     # drei feste, nacheinander liegende Aktivitäten: keine Überlappung
    kanten, reach2 = A._neue_kante(M, 0, 1, [], reach)
    assert kanten == [(0, 1)] and (reach2[0] >> 1) & 1 and A._waehle_paar(M, [0, 0, 0], [4, 4, 4], reach2) == (0, 2)
