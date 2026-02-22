# Architektur

## Alles richtung Architektur (?)

![Architektur](./diagramme/03_architektur_detailliert.drawio.svg)
TODO: Darstellung des Prozesses zur Architektur
TODO: Erklärung der einzelnen Module

TODO: Verlinkung auf Implementierungs.md 

## Statemachine (Luca S)

![Statemachine](./diagramme/04_statemachine.drawio.svg)

Ursprünglich wurde GET, UPSERT und DELETE mit mehreren States designed. Bei der Implementation ist aufgekommen, dass alles mit einem Sate geht.
Die Implementation für DELETE wurde aus Zeitrgründen nicht refactored. 
TODO: (Änderung der Implementation im Ausblick beschreiben oder zumindest in eine Liste eintragen)


TODO: erklären, warum wir sub states wollten
TODO: erklären, Optimierung der States (Insert zunächst drei Zyklen und dann runter auf zwei)

```sv
Beispiel Code wie bei uns die Statemachine in die einzelnen Operationen unterteilt wurde.
cmd.done, cmd.error übergabe
en und enter
```

## Taktzyklus Beispiele (Luca S)

TODO: darstellen der initialen Planung wie wir nur zw. controller und memory block arbeiten wollten
TODO: Takt Diagramm erstellen, welches genau auf die einzelnen Phasen eingeht

![taktzyklus](./diagramme/05_taktzyklus.drawio.svg)

