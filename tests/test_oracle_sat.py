"""Orakel-Test für die zeitindizierte SAT-Kodierung (`kum_sat`): Entscheidungsfassung gegen Aufzählung und CP-SAT, Modell → Plan → unabhängiger Prüfer, gezählte Größe gegen gebaute Kodierung.

Handwerte: Totalizer über 2 Eingänge mit Grenze 1: o1 ← a, o1 ← b, o2 ← a ∧ b und die Verbotsklausel ¬o2, also 2 Hilfsvariablen und 4 Klauseln.
H1 bei H = 7: Fenster P [0, 3], Q [0, 3], U [0, 3], R [1, 4], T [3, 6] (je 4 Startzeitpunkte, 20 Startvariablen); 5 Mindestens-ein-Start-Klauseln, 5 · C(4, 2) = 30 Paarklauseln, 4 + 4 Vorrangklauseln."""

import pytest

import kum_kodierung as K
import kum_sat as S
from kum_scenario import H1, H2, make_instanz
from orakel import alle_plaene, cpsat_entscheidung, ist_plan, optimum


def test_totalizer_zaehlung_von_hand_und_gegen_den_bau():
    assert S.totalizer_groesse(2, 1) == (2, 4) and S.totalizer_groesse(3, 3) == (0, 0) and S.totalizer_groesse(4, 0) == (0, 4)
    for n in range(1, 18):
        for k in range(0, n + 2):
            pool = K.Hilfsvariablen(n)
            klauseln = K.hoechstens_totalizer(list(range(1, n + 1)), k, pool)
            assert S.totalizer_groesse(n, k) == (pool.n - n, len(klauseln)), (n, k)


def test_kodierung_von_hand_h1():
    k = S.kodiere(H1, 7)
    assert k.instanz_variablen == 20 and (k.est, k.lst) == ([0, 0, 0, 1, 3], [3, 3, 3, 4, 6])
    assert k.klauseln[0] == (1, 2, 3, 4) and k.klauseln[1] == (-1, -2)                      # Aktivität P: mindestens ein, dann paarweise höchstens ein Start
    assert len(k.klauseln[:43]) == 43 and all(len(c) == 4 for c in k.klauseln[:5 * 7:7])   # 5 · (1 + 6) = 35 Klauseln der Starts
    assert S.kodiere(H1, 3) is None                                                         # H kürzer als die Kette: Fenster leer, keine Kodierung


def test_gezaehlte_groesse_gleicht_der_gebauten_kodierung():
    for H in (6, 7, 8, 9):
        for inst in (H1, H2):
            k, g = S.kodiere(inst, H), S.groesse(inst, H)
            assert (k is None) == (g is None)
            if k:
                assert g == (k.n_variablen, len(k.klauseln))
    for seed in range(5):
        for n, r, c in ((10, 1, 3), (8, 2, 3), (12, 1, 2)):
            inst = make_instanz(n, r, c, seed)
            from kum_scenario import beste_konstruktion
            H = beste_konstruktion(inst)[0]
            k = S.kodiere(inst, H)
            assert S.groesse(inst, H) == (k.n_variablen, len(k.klauseln))


def _kleine(seeds):
    for seed in seeds:
        yield make_instanz(4, 1, 2, seed, dmax=3, p_vorrang=0.2)
        yield make_instanz(4, 2, 2, seed, dmax=3, p_vorrang=0.2)


def test_entscheidungsfassung_gegen_die_aufzaehlung():
    """Erfüllbar genau dann, wenn es einen Plan mit Makespan ≤ H gibt (H = Optimum − 2 bis Optimum + 1); ein Modell wird in einen Plan zurückübersetzt und vom unabhängigen Prüfer bestätigt."""
    erfuellbar = unerfuellbar = 0
    for inst in _kleine(range(15)):
        opt = optimum(inst)
        for H in range(max(max(inst.d), opt - 2), opt + 2):
            r = S.sat_entscheide(inst, H, budget=50000)
            gibt = bool(alle_plaene(inst, H))
            assert r.antwort is gibt, (inst, H)
            if gibt:
                assert ist_plan(inst, r.plan, H)
                erfuellbar += 1
            else:
                assert r.plan is None
                unerfuellbar += 1
    assert erfuellbar > 20 and unerfuellbar > 10


def test_handbeispiele_erfuellbar_bei_optimum_unerfuellbar_darunter():
    for inst, opt in ((H1, 7), (H2, 8)):
        assert S.sat_entscheide(inst, opt).antwort is True and S.sat_entscheide(inst, opt - 1).antwort is False


def test_gegen_cpsat_bei_n_7():
    pytest.importorskip("ortools")
    for seed in range(3):
        inst = make_instanz(7, 1, 3, seed, dmax=5)
        from orakel import cpsat_optimum
        opt, bewiesen = cpsat_optimum(inst)
        assert bewiesen
        for H in (opt, opt - 1):
            r = S.sat_entscheide(inst, H, budget=50000)
            assert r.antwort is cpsat_entscheidung(inst, H)


def test_randfaelle_bedarf_ueber_kapazitaet_und_budget():
    from kum_scenario import Instanz
    zu_gross = Instanz(d=(2,), bedarf=((3,),), kap=(2,), kanten=())
    assert S.kodiere(zu_gross, 5) is None and S.groesse(zu_gross, 5) is None and S.sat_entscheide(zu_gross, 5).antwort is False
    inst = make_instanz(10, 1, 3, 3)
    assert S.sat_entscheide(inst, 39, budget=3).antwort in (None, True, False)
    assert S.sat_entscheide(inst, 39, budget=3).konflikte <= 3
