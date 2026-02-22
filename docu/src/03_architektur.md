# Architektur

Notiz: Key = 0 bedeutet, dass die Speicherzelle nicht belegt ist (siehe memory_cell)

## Alles richtung Architektur

![Architektur](./diagramme/03_architektur_detailliert.drawio.svg)


## Statemachine

![Statemachine](./diagramme/04_statemachine.drawio.svg)

Ursprünglich wurde GET, UPSERT und DELETE mit mehreren States designed. Bei der Implementation ist aufgekommen, dass alles mit einem Sate geht.
Die Implementation für DELETE wurde aus Zeitrgründen nicht refactored. `(Änderung der Implementation im Ausblick beschreiben oder zumindest in eine Liste eintragen)`


```sv
Beispiel Code wie bei uns die Statemachine in die einzelnen Operationen unterteilt wurde.
cmd.done, cmd.error übergabe
en und enter
```

## Taktzyklus Beispiele

![taktzyklus](./diagramme/05_taktzyklus.drawio.svg)