"""Abbildungen: Aufbau der Figuren an kleinen Eingaben (Zahl der Balken, Pflichtteile, Profil, Achsen gesperrt)."""

import kum_algorithm as A
import kum_visualization as V
from kum_scenario import H1


def test_fenster_hat_je_aktivitaet_einen_balken_und_nur_echte_pflichtteile():
    f = A.fixpunkt(H1, 7, 1)
    fig = V.build_fenster_profil(H1, f.est, f.lst, 7)
    fenster, pflicht, profil = fig.data[:3]
    assert len(fenster.y) == 5
    erwartet = V.pflicht_zeitpunkte(f.est, f.lst, H1.d)
    assert erwartet == [0, 1] and len(pflicht.y) == 2                                  # nur P und Q haben einen Pflichtteil
    for base, x, i in zip(pflicht.base, pflicht.x, erwartet):
        assert (base, base + x) == (f.lst[i], f.est[i] + H1.d[i])
    assert list(profil.y) == [0, 0, 0, 2, 0, 0, 0]
    assert fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange


def test_fensterbalken_reichen_von_est_bis_lct():
    f = A.fixpunkt(H1, 7, 0)
    fenster = V.build_fenster_profil(H1, f.est, f.lst, 7).data[0]
    for i, (base, x) in enumerate(zip(fenster.base, fenster.x)):
        assert (base, base + x) == (f.est[i], f.lst[i] + H1.d[i])


def test_alle_ereignisse_aller_kombinationen_lassen_sich_zeichnen():
    from kum_scenario import H2
    for inst in (H1, H2):
        for H in (6, 7, 8):
            for stufe in (0, 1, 2):
                for e in A.fixpunkt(inst, H, stufe).protokoll.ereignisse:
                    assert len(V.build_fenster_profil(inst, e.est, e.lst, H).data) >= 3


def test_gantt_hat_je_aktivitaet_einen_balken():
    r = A.loese(H1, 1)
    fig = V.build_gantt(H1, r.plan)
    assert len(fig.data) == 5 and list(fig.layout.yaxis.categoryarray) == ["P", "Q", "U", "R", "T"]


def test_verteilung_zeichnet_abbrueche_als_kreuz():
    fig = V.build_verteilung({0: [10, 20, 30], 1: [5, 6, 20001]}, {0: 0, 1: 1}, 20001)
    boxen = [t for t in fig.data if t.type == "box"]
    kreuze = [t for t in fig.data if t.type == "scatter"]
    assert len(boxen) == 2 and len(kreuze) == 1 and list(kreuze[0].y) == [20001] and fig.layout.yaxis.type == "log"


def test_groesse_und_konflikte():
    fig = V.build_groesse({"a": [(5, 100), (10, 1000)]})
    assert list(fig.data[0].x) == [5, 10] and fig.layout.yaxis.type == "log"
    k = V.build_konflikte([("A", 221, 3), ("B", 0, 40)])
    assert list(k.data[0].y) == [221, 0.5] and list(k.data[1].y) == [3, 40]
