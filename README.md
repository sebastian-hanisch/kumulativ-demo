# Kumulativ – Pflichtteile statt Paare – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-kumulativ-demo.streamlit.app/)**

Stück der Linie **SAT und Constraint Programming** (CP-Arm) in der „Konzepte“-Reihe für die Website „Sebastian Hanisch – Operations Research und Machine Learning“. Die Demo zeigt **eine Frage der Constraint-Programmierung** an einem wachsenden Beispiel: Eine **kumulative Ressource** hat eine Kapazität größer 1 und lässt mehrere Aktivitäten zugleich laufen. Wer nur Paare betrachtet, übersieht, was das **Zeitprofil der Pflichtteile** schon weiß: Wo eine Aktivität wegen ihres engen Fensters sicher läuft, ist Kapazität belegt, und die Fenster der anderen schrumpfen (**Timetabling**). Das Vehikel ist das **Ressourcenproblem mit Vorrang** (RCPSP: Aktivitäten mit Dauer und Bedarf, Vorrangkanten, Ziel: kleinster Makespan). Verwandt: [rcpsp-demo](https://github.com/sebastian-hanisch/rcpsp-demo) (dort Prioritätsregeln und CP-SAT als Referenz; hier ein anderes Modell mit allgemeinem Vorranggraph und mehreren Ressourcen, keine Zahl wiederholt), `disjunktiv-edge-finding-demo` (gleiche Linie) (Kapazität 1: der Paar-Test ersetzt dort das Timetabling).

## Warum dieses Problem

Bei Kapazität 1 gilt für zwei Aktivitäten „a vor b **oder** b vor a“. Bei Kapazität 2 dürfen zwei Aktivitäten zugleich laufen, nur drei nicht mehr, wenn jede Bedarf 1 hat: Die Bedingung gilt je **Zeitpunkt**, nicht je Paar. Das **Profil der Pflichtteile** (Zeitraum `[lst, est + Dauer)`, in dem eine Aktivität auf jeden Fall läuft) summiert genau das auf. Die Demo zählt die **Suchknoten** bis zum bewiesenen Optimum bei drei Stufen der Propagation (nur Vorrang, + Timetabling, + Energie-Überlastprüfung) und stellt daneben die Größe der **zeitindizierten SAT-Kodierung** derselben Aufgabe. Zwei Fragen: Wie viel spart das Profil gegenüber reiner Vorrang-Verzweigung, und was bringt die Energieprüfung darüber hinaus?

## Modell

- **Instanz.** Aktivitäten mit ganzzahliger Dauer (1 bis 9) und Bedarf an einer oder zwei Ressourcen der Kapazität C (Bedarf 1 bis C bei 60 % der Aktivitäten je Ressource, jede Aktivität braucht an mindestens einer), Vorrangkanten zwischen Indizes mit Abstand höchstens 6 (Wahrscheinlichkeit 0,12). Alle Zufallsinstanzen kommen aus dem ganzzahligen SplitMix64-Generator, auf jeder Plattform dieselben. Die **Handbeispiele** H1 und H2 haben fünf Aktivitäten und Kapazität 2.
- **Fenster.** Für den Horizont H („Makespan höchstens H“) hat jede Aktivität ein Fenster aus frühestem Start `est` und spätestem Start `lst`; `lct = lst + Dauer`. Der **Pflichtteil** ist `[lst, est + Dauer)`.
- **Stufen der Propagation** (jede enthält die vorige): **0** nur Vorrang (Ressourcen nur gegen schon festgelegte Starts geprüft, nichts beschnitten); **1** Timetabling (Profil der Pflichtteile, Überlast, Verschieben von est und lst); **2** + Energie-Überlastprüfung über Fenster [a, b) (einfache Fassung, **nur Fehlschlag**, **kein Edge-Finding im Sinne der Literatur**).
- **Suche.** Verzweigen zuerst auf die Reihenfolge eines Paares, das sich nach den Fenstern überlappen kann und gemeinsam eine Kapazität überschreitet (kleinste Spielraumsumme, Gleichstand: kleinstes Paar), sonst auf den Start (früheste Zeit oder eine Einheit später). Die Suche beginnt mit der Schranke der besten von fünf seriellen Konstruktionen (für alle Stufen dieselbe); nach jedem Plan sinkt H auf Makespan − 1; sie endet, wenn H die untere Schranke (längste Kette, Energie ⌈Σ Dauer · Bedarf / Kapazität⌉) unterschreitet.
- **Aufwand.** Gezählt werden **Suchknoten** (Zustand nach der Propagation, Wurzel eingeschlossen), Fehlschläge nach Ursache, Runden und Timetabling-Schlüsse, **nie Sekunden**. Ein Knotenbudget bricht ab; ein Abbruch zählt mit Budget + 1 (also 20.001 bei Budget 20.000) und ist eine untere Schranke.
- **Zeitindizierte SAT-Kodierung.** Eine Variable je (Aktivität, Startzeitpunkt im Fenster); je Aktivität genau ein Start, Vorrang als Klauseln, je Ressource und Zeitpunkt die Kapazität als Totalizer (nach Sekundärbeschreibung umgesetzt, Originalquelle nicht gelesen). Die Entscheidungsfassung „Plan mit Makespan höchstens H?“ löst das Kern-CDCL (Konfliktlernen, aus dem Kern-Paket der Linie kopiert).

## Methodik

| Baustein | Datei | Anmerkung |
|---|---|---|
| Mini-CP: Fenster, Vorrang, Timetabling, Energie-Überlastprüfung, Suche, Zähler, Spur | `kum_algorithm.py` | Stufen 0 bis 2; Entscheidungsfassung (`entscheide`), Optimierung (`loese`), Wurzel-Propagation mit Spur (`fixpunkt`); iterative Tiefensuche |
| Instanzen, Handbeispiele, Schranken, serielle Konstruktion, Planprüfer | `kum_scenario.py` | `make_instanz`, `H1`, `H2`, `beste_konstruktion`, `pruefe_plan` |
| Aufzählung aller Startzeitvektoren | `kum_aufzaehlung.py` | der exakte Gegenentwurf für die Handbeispiele |
| Zeitindizierte SAT-Kodierung, Größenzählung, SAT-Entscheidung | `kum_sat.py` | Zählung ohne Bau der Klauseln, getestet gegen die gebaute Kodierung |
| SplitMix64, Totalizer, CDCL | `kum_rng.py`, `kum_kodierung.py`, `kum_cdcl.py` | **Kopien** aus dem Kern-Paket der Linie (Kern-Version im Modulkopf); `tests/test_copies.py` vergleicht sie mit dem Kern-Hash; nichts importiert aus anderen Demos |
| Messreihen, Zählungen, Verdikte | `kum_evaluation.py` | alle Verdikte als reine Funktionen |
| Vorgerechnete Messreihen | `kum_sweeps.json` | Messskript `tools/messung_sweeps.py`; in der App ausdrücklich „vorgerechnet, nicht live“ |

Experimente in der App: **Pflichtteile von Hand** (Fensterbalken mit Pflichtteil und Profil-Treppe gegen die Kapazität, Schieberegler durch jeden Schluss mit Begründung, Horizont 6 bis 8), **Die Stufen im Vergleich** (vorgerechnete Verteilungen der Zellen A bis C, eine Messreihe auf Knopfdruck für A und B, eine Einzelinstanz live), **Was die Energie-Überlastprüfung bringt** (H2 und die Messreihen), **Größe der zeitindizierten SAT-Kodierung** (vorgerechnete Größen und Konflikte, live gezählte Größe und ein Lauf des Kern-CDCL auf der Einzelinstanz).

## Befunde (gemessen, keine Behauptungen)

Messreihen: Zufallsinstanzen mit Dauern 1 bis 9, **je 10 feste Instanzen** (Zufalls-Seeds 0 bis 9) in den Zellen **A** (n = 10, eine Ressource, Kapazität 3), **B** (n = 15, eine Ressource, Kapazität 4) und **C** (n = 20, zwei Ressourcen, Kapazität 4), Knotenbudget 20.000, gemessen in `kum_sweeps.json` mit `tools/messung_sweeps.py` (OR-Tools 9.15.6755, Python 3.14.6); die 37 bewiesenen Optima (Instanz mal Stufe, auf 15 verschiedenen Instanzen) stimmen alle mit dem von OR-Tools CP-SAT bewiesenen Optimum überein, und kein Wert liegt darunter. Die Zahlen stehen in `tests/test_claims.py`. Die Zahlen einer früheren Messung vor dem Bau (anderer Zufallsgenerator, andere Instanzen; nicht Teil dieses Repos) gelten nicht (siehe Korrekturen).

| Frage | Befund |
|---|---|
| **Handbeispiel H1** (Kapazität 2) | Aufzählung aller Startzeitvektoren: optimaler Makespan 7, **24** Pläne mit Makespan höchstens 7, keiner mit höchstens 6. Fenster bei H = 7 nur aus dem Vorrang: P [0, 3], Q [0, 3], U [0, 3], R [1, 4], T [3, 6]; P und Q laufen sicher im Zeitpunkt 3: Profil [0, 0, 0, 2, 0, 0, 0]. Timetabling: U kann im Zeitpunkt 3 nicht laufen (Profil 2 + Bedarf 1 > Kapazität 2), also lst(U) 3 → 2; T ebenso, est(T) 3 → 4. Der Fixpunkt ist gleich den exakten Grenzen über alle 24 Pläne; Summe der Fensterbreiten 15 → 13. **Bei H = 6** scheitert Timetabling an der Wurzel (R hat keinen Startzeitpunkt, der die Zeitpunkte 2 und 3 meidet), reiner Vorrang nicht (`test_algorithm.py`, `test_oracle_kumulativ.py`). |
| **Handbeispiel H2** (T mit Bedarf 2) | Optimum 8, **12** Pläne, keiner mit höchstens 7. Bei H = 8 hat keine Aktivität einen Pflichtteil: Timetabling schließt nichts (Fensterbreiten 24 vorher und nachher). Bei H = 7 schlägt Timetabling **nicht** fehl, aber die Energieprüfung findet im Fenster [0, 7) die Energie 4·1 + 4·1 + 1·1 + 2·1 + 2·2 = **15 > 2 · 7 = 14**. |
| **Knoten der Handbeispiele** | Entscheidungsfassung, Knoten Stufe 0 / 1 / 2: H1 bei H = 7: 18 / 4 / 4, bei H = 6: 95 / 1 / 1; H2 bei H = 8: 22 / 7 / 7, bei H = 7: 91 / 3 / 1 (`test_claim_knoten_der_handbeispiele`). |
| **Timetabling gegen reine Vorrang-Verzweigung** | Instanzen, deren Optimum im Budget bewiesen wird (Stufe 0 / 1 / 2): **A: 7 / 9 / 9 von 10, B: 1 / 3 / 4, C: 0 / 2 / 2**. Median der Knoten in A: **5.354 / 452 / 450** (Stufe 0 gegen Stufe 1: 11,8-fach weniger); 90-%-Wert 20.001 / 2.299 / 2.217. In B und C liegt der Median bei allen Stufen am Budget (20.001, untere Schranke): die Instanzen zeigen dort den Unterschied nur in der Zahl der Beweise und der Lücke. Gilt für diese Verzweigungsregel und Startschranke (`test_claim_timetabling_gegen_vorrang_je_zelle`). |
| **Lücke zum Optimum bei Abbruch** | Bester Wert minus Optimum (Instanzen mit von CP-SAT bewiesenem Optimum), Median / Maximum Stufe 0 / 1 / 2: B: 1 / 4, 0 / 1, 0 / 1; C: 4 / 8, 1 / 3, 1 / 3; A: 0 / 2, 0 / 1, 0 / 0. |
| **Energie-Überlastprüfung (einfache Fassung)** | Unter den Instanzen, die Stufe 1 **und** Stufe 2 beweisen, spart die Energieprüfung im Median an Knoten: **A 0,9 % (9 Instanzen, höchstens 73 %, in 5 Instanzen etwas, in 4 gleich viele Knoten), B 13 % (3 Instanzen, höchstens 53 %), C 8 % (2 Instanzen, höchstens 10 %)**. Nach der vorab festgelegten Schwelle (Median unter 20 % und keine zusätzlich bewiesene Instanz) ist das in A und C **kaum Wirkung**; in B beweist Stufe 2 **eine Instanz mehr** (4 gegen 3 von 10). Seed 4 in A und in B ist an der Wurzel durch die Schranken entschieden (0 Knoten in allen Stufen) und zählt in A als „gleich“. Das sagt nichts über Edge-Finding oder energetisches Schließen der Literatur (`test_claim_energie_je_zelle`, `test_claim_nullknoten_instanzen`). |
| **CP-SAT als Maßstab** | Konflikte von OR-Tools CP-SAT (`AddCumulative`, ein Arbeiter, 60 s): Median **A 81,5** (Maximum 6.033, 10 von 10 bewiesen), **B 8.560,5** (Maximum 657.837, 9 von 10 bewiesen), **C 6.832** (Maximum 928.580, 9 von 10 bewiesen). Konflikte und Knoten sind verschiedene Einheiten, kein Verfahrensvergleich (`test_claim_cpsat_gegenprobe`). |
| **Größe der SAT-Kodierung** | Median über 10 Instanzen je Zelle, H = beste serielle Konstruktion (Variablen / Klauseln): **A 6.141,5 / 20.804,5, B 26.625 / 98.063,5, C 43.069 / 158.784,5, D (n = 30, zwei Ressourcen, Kapazität 5) 184.978,5 / 740.661,5**; die Klauseln wachsen von Zelle zu Zelle um den Faktor 4,7, 1,6 und 4,7 (`test_claim_groesse`). |
| **Konflikte des Kern-CDCL gegen CP-SAT** | Je 6 feste Instanzen (Zufalls-Seeds 0 bis 5), Konfliktbudget 20.000; Konflikte im Median (Maximum) des Kern-CDCL gegen CP-SAT: **Zelle A, H = Optimum (erfüllbar): 82 (651) gegen 2,5 (62)**, Verhältnis der Mediane 32,8; **Zelle A, H = Optimum − 1 (unerfüllbar): 3.453 (20.000) gegen 122 (1.606)**, Verhältnis 28,3, bei einem Abbruch am Budget (Zufalls-Seed 1) und fünf bewiesenen Unerfüllbarkeiten; **Zelle B, H = Optimum: 2.327 (17.904) gegen 403,5 (2.160)**, Verhältnis 5,8. Die Antwort stimmt mit CP-SAT in 17 von 18 Läufen überein (der 18. ist der Abbruch), jedes Modell ist als Plan zurückübersetzt und vom Prüfer bestätigt; in Zelle B, Zufalls-Seed 0, braucht CP-SAT mit 2.160 mehr Konflikte als das Kern-CDCL mit 756. Konflikte beider Löser sind verschiedene Einheiten; ob der Unterschied am Lernen, an der Kodierung oder an CP-SAT liegt, ist **nicht getrennt** (`test_claim_sat_konflikte`). |

## Ehrliche Grenzen

- **Eigene einfache Fassungen, nach Gedächtnis, nicht gegen die Literatur geprüft.** Timetabling und Energie-Überlastprüfung sind selbst geschrieben; zu kumulativer Propagation ist keine Primärquelle gelesen. „Die Energieprüfung bringt kaum Wirkung“ gilt für diese Fassung (nur Fehlschlag, keine Verschiebung von Fenstern), nicht für Edge-Finding oder energetisches Schließen im Sinne der Literatur.
- **Eine Verzweigungsregel, eine Startschranke, kleine Instanzen.** Die Knotenzahlen gelten für diese Regel und die beste von fünf seriellen Konstruktionen als Start, für Dauern 1 bis 9 und Zellen bis n = 20 mit 10 Instanzen je Zelle. Sie sagen nichts über Benchmark-Instanzen (PSPLIB).
- **Knoten sind keine Rechenzeit.** Stufe 1 und 2 kosten je Knoten mehr als Stufe 0; die Kosten je Knoten sind nicht gemessen. Mediane, bei denen Läufe am Budget abbrachen, sind untere Schranken; in B und C liegt der Median selbst am Budget.
- **Zehn Instanzen je Zelle.** Aussagen über Mediane und Anteile (7 gegen 9 gegen 9 von 10) sind entsprechend unsicher; die Energie-Ersparnis in B und C stützt sich auf 3 beziehungsweise 2 Instanzen.
- **SAT gegen CP-SAT ist kein sauberer Vergleich.** Konflikte beider Löser sind verschiedene Einheiten; das Kern-CDCL ist ein lesbarer Python-Löser auf einer zeitindizierten Kodierung mit Totalizer, CP-SAT arbeitet mit einem Intervallmodell und allen Vorverarbeitungen. Ob der Unterschied am Lernen, an der Kodierung oder an der Stärke von CP-SAT liegt, ist **nicht getrennt**.
- **SAT-Größen für Zelle C und D nur gezählt**, nicht gelöst; die Kodierung von Zelle D hat im Median rund 740.000 Klauseln, für einen Python-Löser kaum handhabbar (nicht versucht).
- **Das Optimum der Instanzen, die CP-SAT nicht beweist** (B Zufalls-Seed 9, C ein Seed) ist der CP-SAT-Bestwert nach 60 s; die Lücken stehen nur für Instanzen mit bewiesenem CP-SAT-Optimum.

## Befunde und Korrekturen gegenüber dem Plan

- **Neue Zahlen statt der Messung vor dem Bau.** Diese frühere Messung (Python-Zufallsgenerator, andere Instanzen, anderer Totalizer) nannte für Zelle A einen Median von 3.063 / 50 / 50 Knoten und 7 / 10 / 10 bewiesene Instanzen, für B 1 / 5 / 5, für C 1 / 3 / 3 und Klauseln im Median von 26.830 bis 461.810; mit SplitMix64-Instanzen und dem Kern-Totalizer sind es die oben genannten Zahlen (A 5.354 / 452 / 450, 7 / 9 / 9; B 1 / 3 / 4; C 0 / 2 / 2). Die Richtung bleibt (Timetabling beweist mehr Instanzen als reine Vorrang-Verzweigung, die Energieprüfung wenig), der Faktor im Median ist 11,8 statt 61. Die Zahlen der Vormessung gelten als überholt.
- **Die Energieprüfung hat in einer Zelle eine Wirkung.** Der Plan nannte „gleiche Zahl bewiesener Instanzen in A bis C“; hier beweist Stufe 2 in B eine Instanz mehr (4 gegen 3). In A und C bleibt es bei „kaum Wirkung“ nach der vorab festgelegten Schwelle. Eine einzelne Instanz in einer Reihe von 10 ist ein schwacher Befund.
- **Die Kodierung wächst stärker als geplant.** Der Plan nannte ×2,6, ×3,1, ×2,1 Klauseln je Größenstufe; hier ×4,7, ×1,6, ×4,7, weil die Zellen andere Ressourcen und Kapazitäten haben und H die beste serielle Konstruktion dieser Instanzen ist (Median 34 / 51,5 / 57 / 90). Die Ursache des Wachstums (Fensterbreite gegen Totalizer) ist nicht getrennt gemessen.
- **Zwei Instanzen sind trivial** (A und B, Zufalls-Seed 4: untere Schranke gleich Startschranke, 0 Knoten); sie bleiben in den Reihen und sind benannt.
- **SAT-Konflikte: Verhältnis kleiner als in der früheren Messung.** Die frühere Messung nannte 16- bis 70-mal so viele Konflikte wie CP-SAT; hier sind es 32,8-mal und 28,3-mal in Zelle A und 5,8-mal in B (Verhältnis der Mediane, 6 Instanzen). In Zelle A bei H = Optimum − 1 bricht ein Lauf (Zufalls-Seed 1) am Konfliktbudget von 20.000 ab; die Mediane sind davon nicht berührt, das Maximum ist eine untere Schranke.
- **Optimum für die SAT-Läufe der App** kommt live vom Mini-CP (Stufe 1) und ist bei n > 10 oft nicht bewiesen; die App sagt dann, dass H sich auf den besten gefundenen Wert bezieht.

## Bewusst nicht umgesetzt

- **Kumulatives Edge-Finding und Timetable-Edge-Finding:** nicht gebaut und nicht gemessen; die Demo macht kein Urteil über das Verfahren der Literatur.
- **Energetic-Reasoning-Anpassung der Zeitfenster:** gebaut ist nur die Fehlschlag-Prüfung über Fenster [a, b); eine frühere Messung des Autors (nicht Teil dieses Repos, hier nicht nachprüfbar, anderer Zufallsgenerator) hatte mit einer Fenster verschiebenden Fassung in Zelle B eine Instanz mehr bewiesen (6 statt 5 von 10) und in A und C keine; nicht neu gemessen.
- **Zeit pro Knoten, Multi-Mode, nicht erneuerbare Ressourcen:** nicht gemessen und nicht gebaut.
- **Zeitkontinuierliche SAT-Kodierung (Order-Encoding) und Lazy Clause Generation** für Kumulativ: eigenes Thema der Linie.
- **Benchmark-Instanzen (PSPLIB), PDF-Export:** nicht gebaut.

## Verifikation

- **Kern:** jede Einheit gegen Handrechnung an H1 und H2 (`tests/test_algorithm.py`): Netzplan und Schranken, Planprüfer, Fenster, Pflichtprofil, jeder Timetabling-Schluss mit Wortlaut, der Fehlschlag bei H = 6, die Energie 15 > 14, die Einheiten `_energie`, `_fest_pruefung`, `_waehle_paar`; Randfälle (`tests/test_edge_cases.py`): n = 1, n = 2, Kapazität 1, Bedarf gleich und über der Kapazität, leerer Vorranggraph, Horizont gleich der längsten Kette, Gleichstand, inklusive Grenzen, Budget 0 und 1.
- **Orakel** (`tests/test_oracle_kumulativ.py`, `tests/test_oracle_sat.py`): das Optimum jeder Stufe gegen die **Aufzählung aller Startzeitvektoren** (`itertools.product` mit eigenem Prüfer; 75 Instanzen mit vier Aktivitäten, 24 mit sechs gegen die ausschneidende Aufzählung der Demo, die ihrerseits gegen das volle Produkt geprüft ist) und gegen **OR-Tools CP-SAT** (`AddCumulative`; n = 10, Entscheidungsfassung des Mini-CP bei n = 8, des SAT bei n = 7); **Solidität**: nach dem Fixpunkt jeder Stufe liegt jeder Plan mit Makespan höchstens H in den Fenstern, ein Fehlschlag tritt nur auf, wenn es keinen Plan gibt; Idempotenz, Fenster der höheren Stufe liegen in denen der niedrigeren; Stufe 2 verschiebt nie Fenster; Bedarf 0 ohne Einfluss; Verdoppeln von Kapazität und Bedarf ändert Knoten und Optimum nicht; Optimum nie unter den Schranken; SAT-Kodierung: erfüllbar genau dann, wenn die Aufzählung einen Plan hat (H = Optimum − 2 bis Optimum + 1), das Modell als Plan zurückübersetzt und vom unabhängigen Prüfer bestätigt, gezählte Größe gleich gebauter Kodierung, Totalizer-Zählung gleich gebautem Totalizer für n bis 17. Ein einmaliger Lauf im Scratch-Ordner über 480 Zufallsinstanzen (n = 5 bis 7) fand keinen Fehler (nicht Teil der Testsuite).
- **Zweig-Test:** auf H1 unterscheiden sich Stufe 0 und 1 (Fensterbreiten 15 / 13), auf H2 Stufe 1 und 2 (Fehlschlag nur durch Energie); in den Messreihen ist keine Spalte konstant.
- **Messreihen** (`tests/test_sweeps.py`): die JSON-Datei gegen eine Neuberechnung (Zelle A alle Stufen, B und C die Läufe mit höchstens 3.000 Knoten, Größen, kurze SAT-Läufe) und gegen die Optima von CP-SAT.
- **Kopien** (`tests/test_copies.py`): `kum_rng.py`, `kum_kodierung.py` und `kum_cdcl.py` sind ohne Abweichung gleich der Kern-Version im Modulkopf; Regressionstests des Kerns für die drei Module (`tests/test_kern_cdcl.py`, `test_kern_kodierung.py`, `test_kern_rng.py`).
- **Verdikte** als reine Funktionen, jede Zahl im Text und die Schwelle „kaum Wirkung“ an handgesetzten Werten (`tests/test_verdicts.py`); **Claims:** jede Zahl dieser README (`tests/test_claims.py`, Messung der README für die CP-SAT-Konflikte).
- **Oberfläche:** AppTest-Rauchtest (jeder Knopf, jeder Regler am Minimum und Maximum, alle 18 Kombinationen aus Beispiel, Horizont und Stufe, Messreihe auf Knopfdruck, SAT-Lauf mit jeder Horizontwahl), Layout (Schnellstart in der Seitenleiste, fester Kopf, Hervorhebung), Footer, Laufzeit-Importe.
- **Nicht geprüft:** dunkles Design, echter Mausklick in den Plotly-Diagrammen (nicht anklickbar), Browser auf Telefonbreite.

## Einordnung und Quellen

**Keine Primärquelle zu Timetabling oder energetischer Propagation bei kumulativen Ressourcen ist für die Demo gelesen**; beide Schlüsse sind eigene einfache Fassungen nach Gedächtnis, ihre Korrektheit stützt sich auf die Tests gegen die Aufzählung und CP-SAT, nicht auf die Quelle. Die Aussagen gelten für diese Fassungen. Edge-Finding und energetisches Schließen der Literatur (als Urheber werden Carlier und Pinson sowie Vilím genannt) sind nicht gelesen und nicht gebaut. OR-Tools CP-SAT dient nur als Gegenprobe (nur in den Tests und im Messskript, nie in der App); die CP-SAT-Zahlen in der App sind **vorgerechnet, nicht live** (`kum_sweeps.json`). Der Totalizer ist nach Sekundärbeschreibung umgesetzt (Bailleux und Boufkhad, Original nicht gelesen).

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: vier Experimente, Annahmentabelle, Formeln |
| `kum_algorithm.py` | Mini-CP: Fenster, Vorrang, Timetabling, Energie, Suche, Spur |
| `kum_aufzaehlung.py` | Aufzählung aller Startzeitvektoren |
| `kum_cdcl.py`, `kum_kodierung.py`, `kum_rng.py` | Kopien aus dem Kern-Paket der Linie (CDCL, Totalizer, SplitMix64) |
| `kum_constants.py` | Regler-Grenzen, Zellen, Schwelle, Farben, Presets |
| `kum_evaluation.py` | Statistik der Messreihen, Live-Läufe, Verdikte |
| `kum_layout.py` | Fester Kopf (Stylesheet) |
| `kum_presets.py` | Permalink, Presets (Schnellstart in der Seitenleiste), Zufalls-Seed-Button |
| `kum_sat.py` | Zeitindizierte SAT-Kodierung, Größenzählung, SAT-Entscheidung |
| `kum_scenario.py` | Instanzen, Handbeispiele, Schranken, Konstruktion, Planprüfer |
| `kum_sweeps.json` | vorgerechnete Messreihen (Messskript `tools/messung_sweeps.py`) |
| `kum_visualization.py` | Plotly-Abbildungen: Fenster mit Profil, Plan, Verteilung, Größe, Konflikte |
| `requirements.txt`, `requirements-dev.txt` | Laufzeit (streamlit, plotly); dev: pytest und OR-Tools (nur Gegenprobe) |
| `tools/messung_sweeps.py` | Messskript für `kum_sweeps.json` (braucht OR-Tools) |
| `tests/` | Handrechnung, Orakel, Randfälle, Auswertung, Verdikte, Claims, Messreihen, Presets, Layout, Kopien, Kern-Regression, AppTest-Smoke-Test, Footer, Laufzeit-Importe |

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit und Plotly.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [SAT und CP: Konfliktlernen bis Wahl](https://sebastianhanisch.net/konzepte-sat-constraint-programming.html).
