\newpage
# Einleitung / Idee

[Link zur custom Hardware]() \
[Link zu Risc-V Tapeout]()

Die ursprüngliche Idee dieses Projekts ist der Entwurf und die Implementierung eines kompakten Key-Value-Stores, inspiriert von Redis, auf RTL-Ebene (für FPGAs oder ASICs).

Grund für diese Entscheidung war 

1) die leichte Erweiterbarkeit der Implementierung: Ausgehend von einfachen Operationen konnten wir diese schrittweise erweitern.
2) Einsteigerfreundlich: Dadurch, dass keiner von uns vorher wesentliche Erfahrung mit Hardware Designs hatte, wollten wir ein möglichst leicht zu verstehendes Projekt umsetzen. 
3) Semirealer Use Case: Im Gegenzug zu anderen Projekten hatten wir die Idee etwas umzusetzen, was so ggf. in der Praxis vorkommen könnte. 
4) Leicht verständlich: Innerhalb unserer Gruppe war die Idee leicht verständlich, sodass alle mit einem gleichen / ähnlichem Verständnis starteten.

Grundlegendes Ziel war Speicheroperationen direkt in Hardware abzubilden, um eine hohe Performance und geringe Latenz zu erreichen. Die geplanten Kernfunktionen sind:

*   **Einfügen von Schlüssel-Wert Paaren (Key-Value Insertion)**
*   **Abrufen von Werten anhand von Schlüsseln (Value Retrieval)**
*   **Löschen von Werten anhand von Schlüsseln (Key Deletion)**
*   **Auflisten von Schlüsseln (Key Listing)**
*   **Automatische Ablaufzeit (TTL - Time-to-Live)**


Die Motivation liegt darin, die Effizienz von Key-Value-Speichern durch Hardwarebeschleunigung zu untersuchen und eine Schnittstelle bereitzustellen, die ähnlich wie Software-Caches funktioniert, aber die Vorteile dedizierter Hardware nutzt. 

![Speicherblöcke](./diagramme/02_architektur.drawio.svg)
 
