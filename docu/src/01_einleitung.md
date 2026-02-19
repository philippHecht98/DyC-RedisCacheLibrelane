\newpage
# Einleitung / Idee

Die ursprüngliche Idee dieses Projekts ist der Entwurf und die Implementierung eines kompakten, synthetisierbaren Key-Value-Stores, inspiriert von Redis, auf RTL-Ebene (für FPGAs oder ASICs).

Das Ziel ist es, grundlegende Speicheroperationen direkt in Hardware abzubilden, um eine hohe Performance und geringe Latenz zu erreichen. Die ursprünglich geplanten Kernfunktionen sind:

*   **Einfügen von Schlüssel-Wert Paaren (Key-Value Insertion)**
*   **Abrufen von Werten anhand von Schlüsseln (Value Retrieval)**
*   **Löschen von Werten anhand von Schlüsseln (Key Deletion)**
*   **Auflisten von Schlüsseln (Key Listing)**
*   **Automatische Ablaufzeit (TTL - Time-to-Live)**


Die Motivation liegt darin, die Effizienz von Key-Value-Speichern durch Hardwarebeschleunigung zu untersuchen und eine Schnittstelle bereitzustellen, die ähnlich wie Software-Caches funktioniert, aber die Vorteile dedizierter Hardware nutzt.

![Speicherblöcke](./diagramme/02_architektur.drawio.svg)
