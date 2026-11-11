"""Zeitindizierte SAT-Kodierung des kumulativen Ressourcenproblems (Entscheidungsfassung „gibt es einen Plan mit Makespan höchstens H?“) und ihre Größe.

Variable x[i, t] heißt „Aktivität i startet im Zeitpunkt t“ (t im Fenster [est, lst] aus Vorrang und Horizont H). Klauseln:
  * jede Aktivität startet mindestens einmal (eine Klausel über das Fenster) und höchstens einmal (paarweise: w (w − 1) / 2 Klauseln bei Fensterbreite w);
  * Vorrang (i, j): x[i, t] → ein x[j, t'] mit t' >= t + d_i (eine Klausel je Startzeitpunkt von i);
  * Kapazität: je Ressource r und Zeitpunkt t höchstens cap_r der laufenden Bedarfe wahr (Totalizer aus `kum_kodierung`; ein Bedarf c zählt als c-fach wiederholtes Literal).
Der Totalizer ist nach Sekundärbeschreibung umgesetzt (Originalquelle nicht gelesen)."""

from dataclasses import dataclass
from functools import lru_cache

import kum_cdcl as S
from kum_kodierung import Hilfsvariablen, hoechstens_totalizer
from kum_scenario import Instanz, fruehester_start, makespan, pruefe_plan


def fenster(inst: Instanz, H: int):
    """(est, lst) nur aus Vorrang und Horizont H; None, wenn ein Fenster leer ist (dann gibt es keinen Plan mit Makespan höchstens H)."""
    est = fruehester_start(inst)
    lst = [H - inst.d[i] for i in range(inst.n)]
    nach = inst.nachfolger()
    for i in reversed(range(inst.n)):
        for j in nach[i]:
            lst[i] = min(lst[i], lst[j] - inst.d[i])
    if any(est[i] > lst[i] for i in range(inst.n)):
        return None
    return est, lst


def _laufende(inst: Instanz, est, lst, r: int, t: int) -> list:
    """Literal-Quellen (Aktivität, Startzeitpunkt s, Bedarf) der Ressource r, die im Zeitpunkt t laufen können: s im Fenster mit s <= t < s + d."""
    return [(i, s, inst.bedarf[r][i]) for i in range(inst.n) if inst.bedarf[r][i]
            for s in range(max(est[i], t - inst.d[i] + 1), min(lst[i], t) + 1)]


@dataclass
class Kodierung:
    n_variablen: int
    klauseln: list
    var: dict          # (Aktivität, Startzeitpunkt) → Variablennummer
    est: list
    lst: list
    instanz_variablen: int      # Zahl der Startvariablen x[i, t]; der Rest sind Hilfsvariablen des Totalizers


def kodiere(inst: Instanz, H: int):
    """Die Klauseln der Entscheidungsfassung für den Horizont H; None, wenn schon der Vorrang ein Fenster leer macht oder eine Aktivität mehr Bedarf hat als die Ressource Kapazität."""
    if not inst.zulaessig():
        return None
    fe = fenster(inst, H)
    if fe is None:
        return None
    est, lst = fe
    var = {}
    nv = 0
    for i in range(inst.n):
        for t in range(est[i], lst[i] + 1):
            nv += 1
            var[(i, t)] = nv
    pool = Hilfsvariablen(nv)
    klauseln = []
    for i in range(inst.n):
        lits = [var[(i, t)] for t in range(est[i], lst[i] + 1)]
        klauseln.append(tuple(lits))
        for a in range(len(lits)):
            for b in range(a + 1, len(lits)):
                klauseln.append((-lits[a], -lits[b]))
    for i, j in inst.kanten:
        for t in range(est[i], lst[i] + 1):
            klauseln.append((-var[(i, t)],) + tuple(var[(j, u)] for u in range(max(t + inst.d[i], est[j]), lst[j] + 1)))
    for r in range(inst.ressourcen):
        cap = inst.kap[r]
        for t in range(H):
            lits = []
            for i, s, c in _laufende(inst, est, lst, r, t):
                lits += [var[(i, s)]] * c
            klauseln += hoechstens_totalizer(lits, cap, pool)
    return Kodierung(pool.n, klauseln, var, est, lst, nv)


# --------------------------------------------------------------------------------------------------------------------------------- Größe zählen
@lru_cache(maxsize=None)
def totalizer_groesse(n: int, k: int) -> tuple:
    """(Hilfsvariablen, Klauseln) von `hoechstens_totalizer` für n Eingänge und Grenze k, ohne die Klauseln zu bauen (gleiche Rekursion, nur gezählt)."""
    if k >= n:
        return 0, 0
    if k == 0:
        return 0, n

    def baue(m):
        """(Ausgänge, Hilfsvariablen, Klauseln) des Teilbaums über m Eingänge."""
        if m == 1:
            return 1, 0, 0
        mitte = m // 2
        la, va, ka = baue(mitte)
        lb, vb, kb = baue(m - mitte)
        aus = min(k + 1, la + lb)
        return aus, va + vb + aus, ka + kb + (la + 1) * (lb + 1) - 1

    aus, v, kl = baue(n)
    return v, kl + (1 if aus > k else 0)


def groesse(inst: Instanz, H: int):
    """(Variablen, Klauseln) der Kodierung für den Horizont H, exakt gezählt (stimmt mit `kodiere` überein, getestet); None, wenn es keine Kodierung gibt (Fenster leer)."""
    if not inst.zulaessig():
        return None
    fe = fenster(inst, H)
    if fe is None:
        return None
    est, lst = fe
    var_n = sum(lst[i] - est[i] + 1 for i in range(inst.n))
    kl = 0
    hilf = 0
    for i in range(inst.n):
        w = lst[i] - est[i] + 1
        kl += 1 + w * (w - 1) // 2
    kl += sum(lst[i] - est[i] + 1 for i, _ in inst.kanten)
    for r in range(inst.ressourcen):
        for t in range(H):
            m = sum(c for _, _, c in _laufende(inst, est, lst, r, t))
            v, k = totalizer_groesse(m, inst.kap[r])
            hilf += v
            kl += k
    return var_n + hilf, kl


@dataclass
class SatErgebnis:
    antwort: bool | None        # True: Plan mit Makespan <= H gefunden, False: bewiesen unerfüllbar, None: Budget
    konflikte: int
    variablen: int
    klauseln: int
    plan: list | None


def sat_entscheide(inst: Instanz, H: int, budget: int = 20000, seed: int = 0) -> SatErgebnis:
    """Entscheidungsfassung mit dem Kern-CDCL (Konfliktlernen). Ein Modell wird in einen Plan zurückübersetzt und vom unabhängigen Prüfer kontrolliert (sonst AssertionError)."""
    k = kodiere(inst, H)
    if k is None:
        return SatErgebnis(False, 0, 0, 0, None)
    erg = S.solve(k.n_variablen, k.klauseln, conflict_budget=budget, seed=seed)
    plan = None
    if erg.antwort:
        plan = [next(t for t in range(k.est[i], k.lst[i] + 1) if erg.modell[k.var[(i, t)]]) for i in range(inst.n)]
        ok, grund = pruefe_plan(inst, plan)
        if not ok or makespan(inst, plan) > H:
            raise AssertionError(f"SAT-Modell verletzt die Instanz: {grund or 'Makespan zu groß'}")
    return SatErgebnis(erg.antwort, erg.stat["konflikte"], k.n_variablen, len(k.klauseln), plan)
