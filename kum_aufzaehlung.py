"""Aufzählung aller ganzzahligen Startzeitvektoren (der exakte Gegenentwurf zum Mini-CP, für kleine Instanzen).

Zählt jeden Startzeitvektor mit Makespan höchstens H, der Vorrang und Kapazität einhält. Kein Propagator, keine Fenster: die Aktivitäten werden der Reihe nach auf jeden
Startzeitpunkt gesetzt und gegen die schon gesetzten geprüft (Ausschneiden unzulässiger Teilbelegungen, nie Weglassen zulässiger). Nur für n <= 6 und kleine Dauern gedacht."""

from dataclasses import dataclass

from kum_scenario import Instanz


def plaene(inst: Instanz, H: int, grenze: int | None = None) -> list:
    """Alle Startzeitvektoren (Tupel) mit Makespan höchstens H, die Vorrang und Kapazität einhalten; `grenze` bricht nach so vielen Plänen ab."""
    n = inst.n
    vor = inst.vorgaenger()
    ergebnis = []
    start = [0] * n

    def passt(i, t):
        if t + inst.d[i] > H:
            return False
        if any(start[p] + inst.d[p] > t for p in vor[i] if p < i):
            return False
        for r in range(inst.ressourcen):
            if inst.bedarf[r][i] > inst.kap[r]:
                return False
            for u in range(t, t + inst.d[i]):
                last = inst.bedarf[r][i] + sum(inst.bedarf[r][k] for k in range(i) if start[k] <= u < start[k] + inst.d[k])
                if last > inst.kap[r]:
                    return False
        return True

    def rekursiv(i):
        if grenze is not None and len(ergebnis) >= grenze:
            return
        if i == n:
            if all(start[a] + inst.d[a] <= start[b] for a, b in inst.kanten):                  # Kanten mit größerem Vorgänger-Index gibt es nicht; Sicherheitsprüfung
                ergebnis.append(tuple(start))
            return
        for t in range(0, H - inst.d[i] + 1):
            if passt(i, t):
                start[i] = t
                rekursiv(i + 1)

    rekursiv(0)
    return ergebnis


@dataclass(frozen=True)
class Aufzaehlung:
    optimum: int            # kleinster Makespan
    am_optimum: int         # Pläne mit Makespan höchstens Optimum
    unter_optimum: int      # Pläne mit Makespan höchstens Optimum − 1 (immer 0)


def aufzaehlen(inst: Instanz, hoechst: int = 40) -> Aufzaehlung:
    """Optimum durch Aufzählung: der kleinste Horizont H, für den es einen Plan gibt (ab der längsten Dauer, die kein Makespan unterschreitet)."""
    for H in range(max(1, max(inst.d, default=1)), hoechst + 1):
        if plaene(inst, H, grenze=1):
            return Aufzaehlung(H, len(plaene(inst, H)), len(plaene(inst, H - 1)) if H > 1 else 0)
    raise ValueError("kein Plan bis zum Höchstwert")


def exakte_grenzen(inst: Instanz, H: int) -> tuple:
    """(kleinster, größter) Start je Aktivität über alle Pläne mit Makespan höchstens H; None, wenn es keinen Plan gibt."""
    ps = plaene(inst, H)
    if not ps:
        return None
    return tuple(min(p[i] for p in ps) for i in range(inst.n)), tuple(max(p[i] for p in ps) for i in range(inst.n))
