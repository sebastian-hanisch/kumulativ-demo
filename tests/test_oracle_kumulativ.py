"""Orakel-Test (ORACLE-PLAYBOOK §2, Scheduling): Mini-CP und Propagation gegen einen anderen Rechenweg.

Orakel: (1) Aufzählung **aller** Startzeitvektoren (`orakel.alle_plaene`, `itertools.product` und ein eigener Prüfer), (2) OR-Tools CP-SAT mit `AddCumulative` (im Test-venv; fehlt es, überspringt sich der Teil).
Geprüft werden das Optimum jeder Stufe, die Solidität jedes Schlusses (nie ein Plan abgeschnitten), die Eigenschaften (Idempotenz, Monotonie der Stufen, Skalierung, Schranken)
und die angezeigten Größen (Zähler, Pflichtprofil, Fensterbreite). Die Instanzen stammen aus dem SplitMix64-Erzeuger der Demo, die Handbeispiele aus `kum_scenario`."""

import pytest

import kum_algorithm as A
import kum_aufzaehlung as Z
import kum_scenario as Sc
from kum_scenario import H1, H2, Instanz, make_instanz
from orakel import alle_plaene, cpsat_entscheidung, cpsat_optimum, ist_plan, optimum


def _kleine_instanzen(seeds=range(25)):
    """Drei Formen mit vier Aktivitäten, klein genug für die volle Aufzählung mit `itertools.product` (Dauern höchstens 3)."""
    for seed in seeds:
        yield make_instanz(4, 1, 2, seed, dmax=3, p_vorrang=0.2)
        yield make_instanz(4, 1, 3, seed, dmax=3, p_vorrang=0.3)
        yield make_instanz(4, 2, 2, seed, dmax=3, p_vorrang=0.2)


def _mittlere_instanzen(seeds=range(12)):
    """Sechs Aktivitäten: hier zählt die ausschneidende Aufzählung der Demo (`kum_aufzaehlung`, an den kleinen Instanzen gegen das volle Produkt geprüft)."""
    for seed in seeds:
        yield make_instanz(6, 1, 3, seed, dmax=4, p_vorrang=0.15)
        yield make_instanz(6, 2, 2, seed, dmax=3, p_vorrang=0.15)


# ------------------------------------------------------------------------------------------------------------------------- Handwerte
def test_handbeispiele_gegen_die_aufzaehlung_aller_startzeitvektoren():
    """H1: Optimum 7, 24 Pläne mit Makespan ≤ 7, keiner mit ≤ 6; H2: Optimum 8, 12 Pläne, keiner mit ≤ 7 (hb_14.py, unabhängig nachgerechnet)."""
    assert (optimum(H1), len(alle_plaene(H1, 7)), len(alle_plaene(H1, 6))) == (7, 24, 0)
    assert (optimum(H2), len(alle_plaene(H2, 8)), len(alle_plaene(H2, 7))) == (8, 12, 0)
    az1, az2 = Z.aufzaehlen(H1), Z.aufzaehlen(H2)
    assert (az1.optimum, az1.am_optimum, az1.unter_optimum) == (7, 24, 0) and (az2.optimum, az2.am_optimum) == (8, 12)
    assert set(Z.plaene(H1, 7)) == set(alle_plaene(H1, 7))


def test_exakte_grenzen_der_handbeispiele_und_fixpunkt_h1():
    """H1 bei H = 7: der Fixpunkt des Timetablings ist gleich den exakten Grenzen über alle 24 Pläne."""
    emin, emax = Z.exakte_grenzen(H1, 7)
    f = A.fixpunkt(H1, 7, 1)
    assert f.ok and tuple(f.est) == emin == (0, 0, 0, 1, 4) and tuple(f.lst) == emax == (3, 3, 2, 4, 6)
    emin2, emax2 = Z.exakte_grenzen(H2, 8)
    assert emin2 == (0, 0, 0, 4, 0) and emax2 == (4, 4, 3, 6, 6)


# --------------------------------------------------------------------------------------------------- Aufzählung als Orakel (Optimum, Plan)
def test_die_aufzaehlung_der_demo_stimmt_mit_dem_vollen_produkt_ueberein():
    for inst in list(_kleine_instanzen(range(6))):
        H = optimum(inst)
        assert sorted(Z.plaene(inst, H)) == sorted(alle_plaene(inst, H))
        assert Z.aufzaehlen(inst).optimum == H


def test_optimum_jeder_stufe_gegen_die_aufzaehlung():
    gesehen = 0
    for inst in _kleine_instanzen():
        opt = optimum(inst)
        for stufe in (0, 1, 2):
            r = A.loese(inst, stufe, budget=200000)
            assert r.bewiesen and r.optimum == opt, (inst, stufe, r.optimum, opt)
            assert ist_plan(inst, r.plan, r.optimum) and Sc.makespan(inst, r.plan) == r.optimum
        gesehen += 1
    assert gesehen == 75


def test_entscheidungsfassung_gegen_die_aufzaehlung_fuer_jeden_horizont():
    """Für H = Optimum − 2 bis Optimum + 1: gefunden genau dann, wenn die Aufzählung einen Plan hat; ein gefundener Plan ist ein Plan."""
    for inst in _kleine_instanzen(range(15)):
        opt = optimum(inst)
        for H in range(max(max(inst.d), opt - 2), opt + 2):
            gibt = bool(alle_plaene(inst, H))
            for stufe in (0, 1, 2):
                e = A.entscheide(inst, H, stufe, budget=200000)
                assert e.gefunden is gibt, (inst, H, stufe)
                if gibt:
                    assert ist_plan(inst, e.plan, H)


# ------------------------------------------------------------------------------------------------------------------------- Solidität
def _loesbar_horizonte(inst):
    opt = optimum(inst)
    return [(H, alle_plaene(inst, H)) for H in (opt, opt + 1, opt + 2)]


def test_kein_schluss_schneidet_einen_plan_ab():
    """Nach dem Fixpunkt jeder Stufe liegt jeder Plan mit Makespan ≤ H in den Fenstern [est, lst]; bei Fehlschlag gibt es keinen Plan. Bei H = Optimum − 1 gibt es nie einen Plan."""
    for inst in _kleine_instanzen(range(25)):
        for H, ps in _loesbar_horizonte(inst):
            for stufe in (0, 1, 2):
                f = A.fixpunkt(inst, H, stufe)
                assert f.ok, (inst, H, stufe)
                for p in ps:
                    assert all(f.est[i] <= p[i] <= f.lst[i] for i in range(inst.n)), (inst, H, stufe, p)
        opt = optimum(inst)
        if opt - 1 >= max(inst.d):
            assert not alle_plaene(inst, opt - 1)


def test_fehlschlag_nur_wenn_es_keinen_plan_gibt():
    """Die Umkehrung der Solidität fürs Zählen: scheitert ein Fixpunkt (irgendeine Stufe), gibt es keinen Plan mit Makespan ≤ H."""
    scheitert = {0: 0, 1: 0, 2: 0}
    for inst in _kleine_instanzen(range(30)):
        opt = optimum(inst)
        for H in range(max(max(inst.d), opt - 2), opt + 1):
            gibt = bool(alle_plaene(inst, H))
            for stufe in (0, 1, 2):
                f = A.fixpunkt(inst, H, stufe)
                if not f.ok:
                    assert not gibt
                    scheitert[stufe] += 1
    assert scheitert[1] > scheitert[0]                                           # Timetabling scheitert an der Wurzel häufiger als reiner Vorrang
    assert scheitert[2] >= scheitert[1]


# ----------------------------------------------------------------------------------------------------------------------- Eigenschaften
def test_fixpunkt_ist_idempotent_und_die_stufen_sind_monoton():
    for inst in _kleine_instanzen(range(25)):
        opt = optimum(inst)
        for H in (opt, opt + 2):
            breiten = []
            for stufe in (0, 1, 2):
                f = A.fixpunkt(inst, H, stufe)
                est, lst = list(f.est), list(f.lst)
                M = A.Modell(inst)
                z = A.Zaehler()
                assert A.propagiere(M, est, lst, M.kanten, H, stufe, z)
                assert (est, lst) == (f.est, f.lst) and z.tt_schluesse == 0           # zweiter Lauf ändert nichts
                breiten.append((f.est, f.lst))
            for (e0, l0), (e1, l1) in zip(breiten, breiten[1:]):                           # Fenster der höheren Stufe liegen in denen der niedrigeren
                assert all(a >= b for a, b in zip(e1, e0)) and all(a <= b for a, b in zip(l1, l0))


def test_stufe_2_schliesst_mindestens_so_viel_wie_stufe_1():
    for inst in _kleine_instanzen(range(30)):
        opt = optimum(inst)
        for H in range(max(max(inst.d), opt - 2), opt + 2):
            f1, f2 = A.fixpunkt(inst, H, 1), A.fixpunkt(inst, H, 2)
            assert f2.ok <= f1.ok                                                         # scheitert Stufe 1, scheitert auch Stufe 2
            if f1.ok and f2.ok:
                assert (f1.est, f1.lst) == (f2.est, f2.lst)                               # die Energieprüfung verschiebt keine Fenster


def test_bedarf_null_hat_keinen_einfluss():
    """Eine Aktivität ohne Bedarf wird vom Timetabling nie verschoben (Fenster wie bei Stufe 0) und ändert das Optimum der übrigen nicht."""
    basis = Instanz(d=(3, 3, 2), bedarf=((1, 1, 0),), kap=(1,), kanten=())
    f0, f1 = A.fixpunkt(basis, 6, 0), A.fixpunkt(basis, 6, 1)
    assert f0.ok and f1.ok and (f0.est[2], f0.lst[2]) == (f1.est[2], f1.lst[2]) == (0, 4)
    ohne = Instanz(d=(3, 3), bedarf=((1, 1),), kap=(1,), kanten=())
    for stufe in (0, 1, 2):
        assert A.loese(basis, stufe).optimum == A.loese(ohne, stufe).optimum == 6


def test_verdoppeln_von_kapazitaet_und_bedarf_aendert_nichts():
    for inst in list(_kleine_instanzen(range(10))):
        doppelt = Instanz(inst.d, tuple(tuple(2 * c for c in z) for z in inst.bedarf), tuple(2 * c for c in inst.kap), inst.kanten)
        for stufe in (0, 1, 2):
            a, b = A.loese(inst, stufe, 20000), A.loese(doppelt, stufe, 20000)
            assert (a.optimum, a.bewiesen, a.z.knoten, a.z.fehlschlaege) == (b.optimum, b.bewiesen, b.z.knoten, b.z.fehlschlaege)
        opt = optimum(inst)
        assert (A.fixpunkt(inst, opt, 2).est, A.fixpunkt(inst, opt, 2).lst) == (A.fixpunkt(doppelt, opt, 2).est, A.fixpunkt(doppelt, opt, 2).lst)


def test_optimum_nie_unter_den_schranken():
    for inst in list(_kleine_instanzen(range(30))) + [make_instanz(10, 1, 3, s) for s in range(5)]:
        r = A.loese(inst, 1, 100000)
        assert r.optimum >= Sc.energie_schranke(inst) and r.optimum >= Sc.kettenlaenge(inst) and r.optimum >= Sc.untere_schranke(inst)
        assert r.optimum <= r.start_schranke


def test_gezaehlte_fehlschlaege_ergeben_die_summe_der_ursachen():
    for seed in range(8):
        inst = make_instanz(10, 1, 3, seed)
        for stufe in (0, 1, 2):
            z = A.loese(inst, stufe, 5000).z
            assert z.fehlschlaege == z.fehl_vorrang + z.fehl_fest + z.fehl_timetabling + z.fehl_energie
            assert z.fehl_fest == 0 or stufe == 0
            assert z.fehl_timetabling == 0 or stufe >= 1
            assert z.fehl_energie == 0 or stufe == 2


def test_pflichtprofil_und_fensterbreite_gegen_die_zaehlung_ueber_die_plaene():
    """Das Profil der Pflichtteile ist ein Teil dessen, was in jedem Plan läuft: nie größer als das tatsächliche Profil irgendeines Plans (H1 bei H = 7)."""
    f = A.fixpunkt(H1, 7, 0)
    prof = A.pflichtprofil(H1, f.est, f.lst, 7)
    assert prof == [0, 0, 0, 2, 0, 0, 0]
    for p in alle_plaene(H1, 7):
        wirklich = [sum(H1.bedarf[0][i] for i in range(5) if p[i] <= t < p[i] + H1.d[i]) for t in range(7)]
        assert all(a <= b for a, b in zip(prof, wirklich))
    assert A.fensterbreite(f.est, f.lst) == 15 and A.fensterbreite(*(A.fixpunkt(H1, 7, 1).est, A.fixpunkt(H1, 7, 1).lst)) == 13


# --------------------------------------------------------------------------------------------------------------------------- CP-SAT
def test_optimum_gegen_cpsat_bei_n_10():
    pytest.importorskip("ortools")
    vergleiche = 0
    for seed in range(5):
        inst = make_instanz(10, 1, 3, seed)
        opt, bewiesen = cpsat_optimum(inst)
        assert bewiesen
        r = A.loese(inst, 1, 20000)
        assert r.optimum >= opt                                   # nie unter dem wahren Optimum
        if r.bewiesen:
            assert r.optimum == opt
            vergleiche += 1
    assert vergleiche >= 3


def test_entscheidungsfassung_gegen_cpsat():
    pytest.importorskip("ortools")
    for inst in (H1, H2, make_instanz(8, 1, 3, 1), make_instanz(8, 1, 3, 2), make_instanz(8, 2, 3, 3)):
        opt, bewiesen = cpsat_optimum(inst)
        assert bewiesen
        for H in (opt - 1, opt):
            erwartet = cpsat_entscheidung(inst, H)
            for stufe in (1, 2):
                e = A.entscheide(inst, H, stufe, budget=100000)
                assert e.gefunden is erwartet, (inst, H, stufe)


# --------------------------------------------------------------------------------------------------------------------------- Zweig-Test
def test_jede_stufe_weicht_auf_mindestens_einer_instanz_von_der_nachbarstufe_ab():
    """Keine Spalte mit lauter gleichen Werten: Stufe 0 gegen 1 (Fenster von H1, Knoten), Stufe 1 gegen 2 (H2: Energie schlägt an, Timetabling nicht)."""
    assert A.fensterbreite(*(lambda f: (f.est, f.lst))(A.fixpunkt(H1, 7, 0))) != A.fensterbreite(*(lambda f: (f.est, f.lst))(A.fixpunkt(H1, 7, 1)))
    assert A.fixpunkt(H2, 7, 1).ok and not A.fixpunkt(H2, 7, 2).ok
    knoten = {s: [A.loese(make_instanz(10, 1, 3, seed), s, 5000).z.knoten for seed in range(6)] for s in (0, 1, 2)}
    assert knoten[0] != knoten[1] and knoten[1] != knoten[2]


# ------------------------------------------------------------------------------------------------------ sechs Aktivitäten (ausschneidende Aufzählung)
def test_optimum_und_soliditaet_bei_sechs_aktivitaeten():
    """Aufzählung der Demo (`kum_aufzaehlung`, an den Instanzen mit vier Aktivitäten gegen das volle Produkt geprüft) als Orakel für sechs Aktivitäten."""
    gesehen = 0
    for inst in _mittlere_instanzen():
        az = Z.aufzaehlen(inst)
        for stufe in (0, 1, 2):
            r = A.loese(inst, stufe, 100000)
            assert r.bewiesen and r.optimum == az.optimum and ist_plan(inst, r.plan, r.optimum), (inst, stufe)
        for H in (az.optimum, az.optimum + 1):
            ps = Z.plaene(inst, H)
            for stufe in (0, 1, 2):
                f = A.fixpunkt(inst, H, stufe)
                assert f.ok and all(f.est[i] <= p[i] <= f.lst[i] for p in ps for i in range(inst.n)), (inst, H, stufe)
        if az.optimum - 1 >= max(inst.d):
            assert not Z.plaene(inst, az.optimum - 1)
            for stufe in (1, 2):
                assert A.entscheide(inst, az.optimum - 1, stufe, 100000).gefunden is False
        gesehen += 1
    assert gesehen == 24
