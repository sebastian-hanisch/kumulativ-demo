"""Konstanten: Regler-Grenzen, feste Annahmen, Farben und Presets."""

# Allgemeine Einstellungen (Seitenleiste): die Instanz für den Live-Lauf in Experiment 2 und die Größenzählung in Experiment 4
N_MIN, N_MAX, DEFAULT_N = 5, 30, 6
RES_MIN, RES_MAX, DEFAULT_RES = 1, 2, 1
CAP_MIN, CAP_MAX, DEFAULT_CAP = 2, 5, 2
SEED_MAX, DEFAULT_SEED = 999999, 1
BUDGET_MIN, BUDGET_MAX, DEFAULT_BUDGET = 1000, 50000, 20000          # Knotenbudget der Live-Läufe
LIVE_REIHE_BUDGET = 5000                                             # Knotenbudget der Messreihe auf Knopfdruck (Experiment 2): hält die Reihe in Zelle B bei etwa einer halben Minute

# Experimentbezogene Regler (Hauptbereich)
HB_BEISPIELE = (1, 2)                                                # 1 = H1 (Timetabling), 2 = H2 (Energie)
HB_NAMEN = {1: "H1", 2: "H2"}
HB_HORIZONTS = (6, 7, 8)
DEFAULT_HB_BSP, DEFAULT_HB_H = 1, 7
STAGES = (0, 1, 2)
DEFAULT_HB_STAGE = 1
STAGE_NAMES = {0: "Stufe 0: nur Vorrang", 1: "Stufe 1: + Timetabling", 2: "Stufe 2: + Energie-Überlastprüfung"}
STAGE_SHORT = {0: "Vorrang", 1: "+ Timetabling", 2: "+ Energie"}
CELL_KEYS = ("A", "B", "C")                                          # Zelle der Messreihe (Experiment 2 und 3); Zelle D nur als Größe
SAT_H_WAHL = (0, 1, 2)                                               # Horizont des SAT-Laufs: 0 beste serielle Konstruktion, 1 Optimum, 2 Optimum − 1
SAT_H_NAMEN = {0: "beste serielle Konstruktion", 1: "Optimum (H = Optimum, erfüllbar)", 2: "Optimum − 1 (unerfüllbar)"}
SAT_BUDGET_MIN, SAT_BUDGET_MAX, DEFAULT_SAT_BUDGET = 500, 20000, 5000   # Konfliktbudget des SAT-Live-Laufs

# Messreihen (vorgerechnet in kum_sweeps.json, Messskript tools/messung_sweeps.py): feste Seeds, nie ein einzelner Seed als Befund
ZELLEN = {"A": (10, 1, 3), "B": (15, 1, 4), "C": (20, 2, 4), "D": (30, 2, 5)}     # (Aktivitäten n, Ressourcen, Kapazität)
SWEEP_SEEDS = tuple(range(10))
SWEEP_BUDGET = 20000                       # Knotenbudget der Stufenreihen
SAT_SEEDS = tuple(range(6))                # SAT-Konfliktmessung: die ersten sechs Seeds der Zelle
SAT_BUDGET = 20000                         # Konfliktbudget der SAT-Messung
SWEEPS_FILE = "kum_sweeps.json"
MEASURE_SCRIPT = "tools/messung_sweeps.py"

# Verdikt „Energie-Überlastprüfung: kaum Wirkung“: vor der Messung festgelegt (Plan), getestet in tests/test_verdicts.py.
# Gemessen wird an den Instanzen, die Stufe 1 UND Stufe 2 beweisen: Ersparnis je Instanz = (Knoten Stufe 1 − Knoten Stufe 2) / Knoten Stufe 1.
SCHWELLE_KAUM_WIRKUNG = 0.20               # Median der Ersparnis unter 20 % und keine zusätzlich bewiesene Instanz: „kaum Wirkung“

COLOR_WINDOW = "rgba(76,120,168,0.28)"
COLOR_WINDOW_LINE = "#4c78a8"
COLOR_MANDATORY = "#2F6B65"
COLOR_HORIZON = "#c0392b"
COLOR_CAPACITY = "#c0392b"
COLOR_PROFILE = "rgba(47,107,101,0.75)"
COLOR_STAGE = {0: "#9a9a9a", 1: "#4c78a8", 2: "#2F6B65"}

_PRESET_INSTANZ_HB = {"seed": DEFAULT_SEED, "n": DEFAULT_N, "res": DEFAULT_RES, "cap": DEFAULT_CAP, "budget": DEFAULT_BUDGET}
PRESETS = {
    "Handbeispiel H1 (Timetabling)": {**_PRESET_INSTANZ_HB, "bsp": 1, "h": 7, "stufe": 1, "zelle": 0, "sat_h": 0, "sat_budget": DEFAULT_SAT_BUDGET},
    "Handbeispiel H2 (Energie)": {**_PRESET_INSTANZ_HB, "bsp": 2, "h": 7, "stufe": 2, "zelle": 0, "sat_h": 0, "sat_budget": DEFAULT_SAT_BUDGET},
    "Zelle A (n = 10)": {"seed": 3, "n": 10, "res": 1, "cap": 3, "budget": DEFAULT_BUDGET, "bsp": 1, "h": 7, "stufe": 1, "zelle": 0, "sat_h": 1, "sat_budget": DEFAULT_SAT_BUDGET},
    "Zelle B (n = 15)": {"seed": 3, "n": 15, "res": 1, "cap": 4, "budget": DEFAULT_BUDGET, "bsp": 1, "h": 7, "stufe": 1, "zelle": 1, "sat_h": 0, "sat_budget": DEFAULT_SAT_BUDGET},
}
PRESET_HELP = {
    "Handbeispiel H1 (Timetabling)": "Fünf Aktivitäten, Kapazität 2: Die Pflichtteile von P und Q belegen den Zeitpunkt 3 voll, also schrumpfen die Fenster von U und T. Bei Horizont 6 scheitert Timetabling an der Wurzel.",
    "Handbeispiel H2 (Energie)": "Dasselbe Beispiel mit Aktivität T von Bedarf 2: Bei Horizont 7 hat keine Aktivität einen Pflichtteil, Timetabling schließt nichts, aber die Energie im Fenster [0, 7) ist 15 und damit größer als 2 · 7.",
    "Zelle A (n = 10)": "Zufallsinstanz mit 10 Aktivitäten, einer Ressource der Kapazität 3 (Zufalls-Seed 3) für Stufenvergleich und Größe der SAT-Kodierung.",
    "Zelle B (n = 15)": "Zufallsinstanz mit 15 Aktivitäten, einer Ressource der Kapazität 4 (Zufalls-Seed 3): die Stufen im Vergleich; hier beweist nicht mehr jede Stufe jede Instanz im Budget.",
}
