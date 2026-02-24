# Learnings (alle)

Nachfolgend werden unsere Learnings während der Entwicklung des Caches und der zugehörigen Toolchain beschrieben. Hierbei werden sowohl Learnings bezüglich der Implementierung als auch der generellen Arbeitsweise und des Projektmanagements beschrieben.

1) Hardware Implementierungs sind aus Sicht eines Softwareentwicklers deutlich umständlicher als Software. Hardware verhält sich anders als Software und muss anders angedacht werden. 
2) Ein modularisiertes Design ermöglichte uns, die Arbeiten a) parallel zu bearbeiten und b) die Komplexität der einzelnen Module möglichst gering zu halten.
3) Selbst mit minimaler Anzahl an Featuren und mit der Idee der Erweiterung, hätten wir nicht gedacht, dass die Implementierung des Chips und die Integration in Croc so komplex sein würde.
4) Das Aufsetzen von Pipelines und Testautomatisierung über GitHub Actions ist für einen Projekt Scope von zwei Wochen zu aufwändig. Zuletzt wurden Tests als auch die Backendpipeline lokal ausgeführt. 
