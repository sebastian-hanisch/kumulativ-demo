"""Randfälle, an denen Kernroutinen erfahrungsgemäß brechen (DEMO-PLAYBOOK §12): n = 1, n = 2, Kapazität 1, Bedarf gleich und über der Kapazität, leerer Vorranggraph,
Horizont gleich der längsten Kette, Gleichstände, inklusive Grenzen."""

import kum_algorithm as A
import kum_aufzaehlung as Z
import kum_scenario as Sc
from kum_scenario import Instanz, make_instanz
from orakel import alle_plaene, optimum


def test_eine_aktivitaet():
    inst = Instanz(d=(3,), bedarf=((1,),), kap=(2,), kanten=())
    for stufe in (0, 1, 2):
        r = A.loese(inst, stufe)
        assert r.optimum == 3 and r.bewiesen and r.plan == [0]
        assert A.entscheide(inst, 3, stufe).gefunden is True and A.entscheide(inst, 2, stufe).gefunden is False


def test_genau_zwei_aktivitaeten():
    """Zwei Aktivitäten mit Bedarf 1 bei Kapazität 2 laufen zugleich (Optimum 3); bei Kapazität 1 nacheinander (Optimum 6)."""
    zusammen = Instanz(d=(3, 3), bedarf=((1, 1),), kap=(2,), kanten=())
    nacheinander = Instanz(d=(3, 3), bedarf=((1, 1),), kap=(1,), kanten=())
    for stufe in (0, 1, 2):
        assert A.loese(zusammen, stufe).optimum == 3 and A.loese(nacheinander, stufe).optimum == 6
    assert optimum(zusammen) == 3 and optimum(nacheinander) == 6


def test_kapazitaet_1_entspricht_der_disjunktion():
    """Bei Kapazität 1 und ohne Vorrang ist der Makespan die Summe der Dauern (eine Maschine); mit Kette ändert sich daran nichts."""
    for seed in range(8):
        inst = make_instanz(5, 1, 1, seed, dmax=4, p_vorrang=0.0)
        inst = Instanz(inst.d, tuple(tuple(1 if c else 0 for c in z) for z in inst.bedarf), (1,), ())
        summe = sum(d for i, d in enumerate(inst.d) if inst.bedarf[0][i])
        for stufe in (0, 1, 2):
            assert A.loese(inst, stufe, 100000).optimum == max(summe, max(inst.d))


def test_bedarf_gleich_kapazitaet_und_ueber_kapazitaet():
    gleich = Instanz(d=(2, 2), bedarf=((2, 2),), kap=(2,), kanten=())
    assert all(A.loese(gleich, s).optimum == 4 for s in (0, 1, 2))
    ueber = Instanz(d=(2, 2), bedarf=((3, 1),), kap=(2,), kanten=())
    assert not ueber.zulaessig()
    for stufe in (0, 1, 2):
        r = A.loese(ueber, stufe)
        assert r.optimum is None and r.bewiesen and r.z.knoten == 0
        assert A.entscheide(ueber, 20, stufe).gefunden is False                  # die Propagation allein erkennt: keine Aktivität darf laufen
    assert not alle_plaene(ueber, 6)


def test_leerer_vorranggraph_und_horizont_gleich_laengster_kette():
    kette = Instanz(d=(2, 3, 1), bedarf=((1, 1, 1),), kap=(5,), kanten=((0, 1), (1, 2)))
    assert Sc.kettenlaenge(kette) == 6
    for stufe in (0, 1, 2):
        e = A.entscheide(kette, 6, stufe)
        assert e.gefunden is True and e.plan == [0, 2, 5] and A.entscheide(kette, 5, stufe).gefunden is False
        f = A.fixpunkt(kette, 6, stufe)
        assert f.ok and A.fensterbreite(f.est, f.lst) == 0                         # Horizont gleich Kette: alle Fenster einpunktig
    leer = Instanz(d=(2, 2, 2), bedarf=((1, 1, 1),), kap=(3,), kanten=())
    assert all(A.loese(leer, s).optimum == 2 for s in (0, 1, 2))


def test_gleichstand_der_paarwahl_und_der_aufzaehlung():
    inst = Instanz(d=(2, 2), bedarf=((2, 2),), kap=(2,), kanten=())
    assert len(Z.plaene(inst, 4)) == 2 and set(Z.plaene(inst, 4)) == {(0, 2), (2, 0)}       # beide Reihenfolgen, gleicher Makespan
    assert A.loese(inst, 1).plan in ([0, 2], [2, 0])


def test_horizont_grenzen_sind_inklusive():
    """Makespan höchstens H ist inklusive: bei H = Optimum gibt es einen Plan, bei H = Optimum − 1 keinen; das Budget 1 reicht für die Wurzel, Budget 0 nicht."""
    inst = Instanz(d=(2, 2), bedarf=((2, 2),), kap=(2,), kanten=())
    assert A.entscheide(inst, 4, 1).gefunden is True and A.entscheide(inst, 3, 1).gefunden is False
    assert A.entscheide(inst, 3, 1, budget=1).gefunden is False and A.entscheide(inst, 3, 1, budget=0).gefunden is None


def test_aufzaehlung_ohne_plan_und_grenze():
    assert Z.exakte_grenzen(Instanz(d=(2, 2), bedarf=((2, 2),), kap=(2,), kanten=()), 3) is None
    assert len(Z.plaene(make_instanz(4, 1, 3, 0, dmax=3), 12, grenze=3)) == 3
