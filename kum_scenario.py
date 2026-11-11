"""Instanzen des kumulativen Ressourcenproblems (RCPSP mit erneuerbaren Ressourcen), Handbeispiele, Schranken, serielle Konstruktion und unabhängiger Planprüfer.

Eine Aktivität i hat eine ganzzahlige Dauer d_i >= 1 und je Ressource r einen Bedarf (0 erlaubt); die Ressource r hat die Kapazität cap_r. Ein Plan ist ein Startzeitvektor s:
Vorrangkante (i, j) heißt s_i + d_i <= s_j, und in jedem Zeitpunkt t ist die Summe der Bedarfe der laufenden Aktivitäten (s_i <= t < s_i + d_i) höchstens cap_r.
Ziel: kleinster Makespan max_i (s_i + d_i).

Der Erzeuger ist eigener Code dieser Demo (nicht der aus rcpsp-demo: dort Ketten mit je einer Ressource, hier ein allgemeiner Vorranggraph mit Bedarf an mehreren Ressourcen).
Zufall nur über den ganzzahligen SplitMix64 (`kum_rng`), nie Python-`random` oder `hash()`: auf jeder Plattform dieselben Instanzen."""

import math
from dataclasses import dataclass

from kum_rng import SplitMix64


@dataclass(frozen=True)
class Instanz:
    """Dauern, Bedarf je Ressource und Aktivität (`bedarf[r][i]`), Kapazität je Ressource, Vorrangkanten (i, j) mit i < j, Namen der Aktivitäten (nur zur Anzeige)."""

    d: tuple
    bedarf: tuple
    kap: tuple
    kanten: tuple
    namen: tuple = ()

    @property
    def n(self) -> int:
        return len(self.d)

    @property
    def ressourcen(self) -> int:
        return len(self.kap)

    def name(self, i: int) -> str:
        return self.namen[i] if self.namen else f"A{i + 1}"

    def zulaessig(self) -> bool:
        """Falsch, wenn eine Aktivität mehr Bedarf hat, als die Ressource Kapazität hat (dann gibt es keinen Plan)."""
        return all(self.bedarf[r][i] <= self.kap[r] for r in range(self.ressourcen) for i in range(self.n))

    def nachfolger(self) -> list:
        nach = [[] for _ in range(self.n)]
        for i, j in self.kanten:
            nach[i].append(j)
        return nach

    def vorgaenger(self) -> list:
        vor = [[] for _ in range(self.n)]
        for i, j in self.kanten:
            vor[j].append(i)
        return vor


# ------------------------------------------------------------------------------------------------------------------------------ Handbeispiele
# Kapazität 2, eine Ressource; Aktivität (Dauer, Bedarf). Von Hand nachgerechnet (README, tests/test_algorithm.py).
H1 = Instanz(d=(4, 4, 1, 2, 1), bedarf=((1, 1, 1, 1, 1),), kap=(2,), kanten=((2, 3), (3, 4)), namen=("P", "Q", "U", "R", "T"))      # Vorrang U → R → T
H2 = Instanz(d=(4, 4, 1, 2, 2), bedarf=((1, 1, 1, 1, 2),), kap=(2,), kanten=((2, 3),), namen=("P", "Q", "U", "R", "T"))              # Vorrang U → R, T braucht Bedarf 2
HANDBEISPIELE = {"H1": H1, "H2": H2}


# ------------------------------------------------------------------------------------------------------------------------------ Erzeuger
def make_instanz(n: int, ressourcen: int, kap: int, seed: int, p_vorrang: float = 0.12, spanne: int = 6, p_bedarf: float = 0.6, dmax: int = 9) -> Instanz:
    """Zufallsinstanz: Dauern 1 bis `dmax`; je Ressource Bedarf 1 bis `kap` bei einem Anteil `p_bedarf` der Aktivitäten (sonst 0; jede Aktivität braucht mindestens eine Ressource);
    Vorrangkanten (i, j) zwischen Indizes mit Abstand höchstens `spanne` mit Wahrscheinlichkeit `p_vorrang`. Alle Ziehungen kommen aus einem SplitMix64-Strom,
    der nur von (n, ressourcen, kap, seed) abhängt."""
    rng = SplitMix64(seed * 1_000_003 + n * 1_009 + ressourcen * 101 + kap)
    d = [1 + rng.below(dmax) for _ in range(n)]
    bedarf = []
    for _ in range(ressourcen):
        zeile = []
        for _ in range(n):
            nutzt = rng.random() < p_bedarf
            wert = 1 + rng.below(kap)                  # immer gezogen, damit der Strom nicht vom Ausgang der Münze abhängt
            zeile.append(wert if nutzt else 0)
        bedarf.append(zeile)
    for i in range(n):
        if all(bedarf[r][i] == 0 for r in range(ressourcen)):
            bedarf[rng.below(ressourcen)][i] = 1 + rng.below(kap)
    kanten = tuple((i, j) for i in range(n) for j in range(i + 1, min(n, i + 1 + spanne)) if rng.random() < p_vorrang)
    return Instanz(tuple(d), tuple(tuple(z) for z in bedarf), (kap,) * ressourcen, kanten)


# ------------------------------------------------------------------------------------------------------------------------------ Schranken
def fruehester_start(inst: Instanz) -> list:
    """Frühester Start nur aus dem Vorrang (Netzplan); die Kanten gehen von kleinem zu großem Index."""
    est = [0] * inst.n
    for i in range(inst.n):
        for j in inst.nachfolger()[i]:
            est[j] = max(est[j], est[i] + inst.d[i])
    return est


def kettenlaenge(inst: Instanz) -> int:
    """Länge der längsten Vorrangkette (kritischer Weg)."""
    est = fruehester_start(inst)
    return max((est[i] + inst.d[i] for i in range(inst.n)), default=0)


def energie_schranke(inst: Instanz) -> int:
    """⌈Σ d_i · bedarf_i / Kapazität⌉, größter Wert über die Ressourcen."""
    return max((math.ceil(sum(inst.d[i] * inst.bedarf[r][i] for i in range(inst.n)) / inst.kap[r]) for r in range(inst.ressourcen)), default=0)


def untere_schranke(inst: Instanz) -> int:
    return max(kettenlaenge(inst), energie_schranke(inst))


# ------------------------------------------------------------------------------------------------------------------------------ Planprüfer
def makespan(inst: Instanz, start) -> int:
    return max((start[i] + inst.d[i] for i in range(inst.n)), default=0)


def pruefe_plan(inst: Instanz, start) -> tuple:
    """Unabhängiger Prüfer: (True, "") oder (False, Grund). Prüft Starts >= 0, jede Vorrangkante und in jedem Zeitpunkt jede Kapazität (nach Zeitpunkten, nicht nach Aktivitätspaaren)."""
    if len(start) != inst.n or any(s < 0 for s in start):
        return False, "Start fehlt oder ist negativ"
    for i, j in inst.kanten:
        if start[i] + inst.d[i] > start[j]:
            return False, f"Vorrang {inst.name(i)} vor {inst.name(j)} verletzt"
    for r in range(inst.ressourcen):
        for t in range(makespan(inst, start)):
            last = sum(inst.bedarf[r][i] for i in range(inst.n) if start[i] <= t < start[i] + inst.d[i])
            if last > inst.kap[r]:
                return False, f"Ressource {r + 1} im Zeitpunkt {t}: Bedarf {last} > Kapazität {inst.kap[r]}"
    return True, ""


# ------------------------------------------------------------------------------------------------------------------------------ Serielle Konstruktion
def _serie(inst: Instanz, schluessel) -> list:
    """Serielle Konstruktion: Aktivitäten nach `schluessel` unter den startbereiten (alle Vorgänger geplant); jede bekommt den frühesten ressourcenzulässigen Start."""
    n = inst.n
    vor = inst.vorgaenger()
    horizont = sum(inst.d) + 1
    last = [[0] * (horizont + max(inst.d) + 2) for _ in range(inst.ressourcen)]
    start = [None] * n
    for _ in range(n):
        bereit = [i for i in range(n) if start[i] is None and all(start[p] is not None for p in vor[i])]
        i = min(bereit, key=schluessel)
        t = max([start[p] + inst.d[p] for p in vor[i]] + [0])
        while any(last[r][u] + inst.bedarf[r][i] > inst.kap[r] for r in range(inst.ressourcen) for u in range(t, t + inst.d[i])):
            t += 1
        start[i] = t
        for r in range(inst.ressourcen):
            for u in range(t, t + inst.d[i]):
                last[r][u] += inst.bedarf[r][i]
    return start


def beste_konstruktion(inst: Instanz):
    """Beste von fünf seriellen Konstruktionen (Reihenfolge nach Index, spätestem Ende, Spielraum, Energie, Dauer): (Makespan, Starts), für alle Stufen dieselbe Startschranke.
    Mit einer Aktivität, deren Bedarf die Kapazität übersteigt, gibt es keinen Plan: None."""
    if not inst.zulaessig():
        return None
    n = inst.n
    nach = inst.nachfolger()
    kette = kettenlaenge(inst)
    spaet = [kette] * n                                   # spätestes Ende bei der Kettenlänge als Horizont
    for i in reversed(range(n)):
        for j in nach[i]:
            spaet[i] = min(spaet[i], spaet[j] - inst.d[j])
    schluessel = [
        lambda i: i,
        lambda i: (spaet[i], i),
        lambda i: (spaet[i] - inst.d[i], i),
        lambda i: (-sum(inst.bedarf[r][i] * inst.d[i] for r in range(inst.ressourcen)), i),
        lambda i: (-inst.d[i], i),
    ]
    beste = None
    for s in schluessel:
        start = _serie(inst, s)
        cm = makespan(inst, start)
        if beste is None or cm < beste[0]:
            beste = (cm, start)
    return beste
