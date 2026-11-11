"""Regressionstests des kopierten Moduls `kum_rng` (Werte aus sat-cp-planung/kern/tests/test_rng_instanzen_dpll.py; Referenzwerte der SplitMix64-Konvention von Vigna)."""

from kum_rng import SplitMix64


def test_splitmix_bekannte_werte():
    # Veröffentlichte Referenzwerte der SplitMix64-Konvention für Seed 0 (Vigna) und Seed 12345
    g = SplitMix64(0)
    assert [g.next() for _ in range(3)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F]
    assert [SplitMix64(12345).next() for _ in range(1)] == [2454886589211414944]
    h = SplitMix64(12345)
    assert [h.next() for _ in range(3)] == [2454886589211414944, 3778200017661327597, 2205171434679333405]


def test_hilfsmethoden():
    g = SplitMix64(5)
    xs = [g.random() for _ in range(1000)]
    assert all(0 <= x < 1 for x in xs) and 0.45 < sum(xs) / 1000 < 0.55
    liste = list(range(20))
    SplitMix64(3).shuffle(liste)
    assert sorted(liste) == list(range(20)) and liste != list(range(20))
    probe = SplitMix64(3).sample(range(50), 7)
    assert len(set(probe)) == 7
    assert SplitMix64(3).sample(range(50), 7) == probe          # deterministisch
    assert SplitMix64(1).randrange(10) == SplitMix64(1).below(10)
