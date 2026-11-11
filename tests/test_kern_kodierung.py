"""Regressionstests des kopierten Moduls `kum_kodierung` (aus sat-cp-planung/kern/tests/test_kodierung_vorverarbeitung_probsat.py, Abschnitt Kodierungen; Importe auf kum_ umgestellt)."""
import itertools
from math import comb

import pytest

from kum_cdcl import solve
from kum_kodierung import (Hilfsvariablen, genau, hoechstens, hoechstens_eins, klauselzahl_binomial, klauselzahl_sinz,
                           mindestens)


def zaehle_loesungen(n, klauseln, n_gesamt, belegung):
    """Gibt zurück, ob die Eingaben 1..n mit `belegung` (Tupel von bool) mit den Klauseln (samt Hilfsvariablen) erfüllbar sind."""
    einheiten = [((i + 1) if b else -(i + 1),) for i, b in enumerate(belegung)]
    return solve(n_gesamt, list(klauseln) + einheiten).antwort is True


@pytest.mark.parametrize("verfahren", ["binomial", "sinz", "totalizer"])
def test_hoechstens_exakt_gegen_aufzaehlung(verfahren):
    n = 6
    for k in range(0, n + 1):
        pool = Hilfsvariablen(n)
        kl = hoechstens(list(range(1, n + 1)), k, pool, verfahren)
        for bits in itertools.product([False, True], repeat=n):
            erwartet = sum(bits) <= k
            assert zaehle_loesungen(n, kl, pool.n, bits) == erwartet, (verfahren, k, bits)


@pytest.mark.parametrize("verfahren", ["binomial", "sinz", "totalizer"])
def test_mindestens_und_genau_gegen_aufzaehlung(verfahren):
    n = 5
    for k in range(0, n + 2):
        pool_m, pool_g = Hilfsvariablen(n), Hilfsvariablen(n)
        km = mindestens(list(range(1, n + 1)), k, pool_m, verfahren)
        kg = genau(list(range(1, n + 1)), k, pool_g, verfahren)
        for bits in itertools.product([False, True], repeat=n):
            assert zaehle_loesungen(n, km, pool_m.n, bits) == (sum(bits) >= k), (verfahren, k, bits)
            assert zaehle_loesungen(n, kg, pool_g.n, bits) == (sum(bits) == k), (verfahren, k, bits)


def test_negierte_literale_und_hoechstens_eins():
    # höchstens 1 von (¬x1, x2, ¬x3): mit x1 = x3 = falsch sind ¬x1 und ¬x3 beide wahr: verboten
    pool = Hilfsvariablen(3)
    kl = hoechstens([-1, 2, -3], 1, pool, "sinz")
    assert not zaehle_loesungen(3, kl, pool.n, (False, False, False))
    assert zaehle_loesungen(3, kl, pool.n, (True, True, True))        # nur x2 ist wahr: genau eines
    assert not zaehle_loesungen(3, kl, pool.n, (True, True, False))   # x2 und ¬x3 beide wahr: zwei
    assert len(hoechstens_eins([1, 2, 3])) == 3


def test_klauselzahlen_formeln():
    for n, k in [(5, 1), (6, 2), (10, 4), (20, 7)]:
        pool = Hilfsvariablen(n)
        kl = hoechstens(list(range(1, n + 1)), k, pool, "sinz")
        assert len(kl) == klauselzahl_sinz(n, k) == 2 * n * k + n - 3 * k - 1      # Sinz 2005, nachgerechnet
        assert pool.n - n == (n - 1) * k                                             # Hilfsvariablen
        pool_b = Hilfsvariablen(n)
        assert len(hoechstens(list(range(1, n + 1)), k, pool_b, "binomial")) == klauselzahl_binomial(n, k) == comb(n, k + 1)
        assert pool_b.n == n
    assert klauselzahl_sinz(10, 0) == 10 and klauselzahl_sinz(3, 3) == 0
    assert klauselzahl_binomial(25, 5) == 177100 and klauselzahl_sinz(25, 5) == 259


def test_randfaelle():
    pool = Hilfsvariablen(3)
    assert hoechstens([1, 2, 3], 3, pool, "sinz") == [] and pool.n == 3
    assert mindestens([1, 2], 3, Hilfsvariablen(2)) == [()]
    assert mindestens([1, 2], 0, Hilfsvariablen(2)) == []
    assert solve(2, mindestens([1, 2], 3, Hilfsvariablen(2))).antwort is False
