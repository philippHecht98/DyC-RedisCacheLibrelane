# Projekt Setup

## Repo Struktur

Zunächst befassten wir uns mit dem Aufbau einer generellen Code Struktur sowie dem Aufsetzen von [#Pipelines](Pipelines). Hierfür wurde zunächst 
ein *Fork* des vom Dozenten bereit gestelltem [GitHub Repostory](https://github.com/hm-aemy/librelane-template) aufgesetzt. 
Der *Fork* wurde verwendet um eine generelle Vorgabe für die Code Struktur zu erlangen. Darauf aufbauend wurden folgende Verzeichnisse angelegt:

- .github/Workflows
- docs
- src TODO: Ausweiten auf die einzelnen Module

Zusätzlich wurden eigens geschriebene Dockerfiles sowie Makefile Targets erstellt, welche uns ermöglichen, komfortabler während der Projektphase
zu arbeiten. Innerhalb der Dockerfile werden benötigte Bibliotheken (bspw. Verilator) installiert. Die Makefile ermöglicht es uns, rekursiv die
einzelnen Sub-Module des Projektes () zu bauen als auch zu testen.

## Pipelines
 
Als ersten wichtigen Punkt für das Zusammenarbeiten während der Projektphase wurde das Aufsetzen von Pipelines angegangen. Hierbei wurden zwei 
GitHub Workflows implementiert, welche unabhängig voneinander eine Frontend / Backendpipeline triggern. Aufgabe der Frontend Pipeline ist das 
ausführen sämtlicher Tests für die Submodule als E2E Tests der gesamten Hardware. 

Die Backend Pipeline wird beim mergen auf den *Main*-Branch aufgerufen und führt die in der Einleitung gezeigten Librelane Pipeline aus. 


TODO: weiteres Repository für tapeout darstellen;
TODO: Detailierter auf Pipeline eingehen (act zum lokalen testen anmerken?)

TODO: ausblick, dass backendpipeline nie ausgeführt wurde, da keine Zeit, zu komplex und eigentlich falsches Repo?