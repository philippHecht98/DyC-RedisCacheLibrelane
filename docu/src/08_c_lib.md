\newpage
# C Lib

Ausarbeitung Luca Pinnekamp

Um die Interaktion mit dem Hardware-Redis-Cache aus einer Software-Umgebung heraus zu vereinfachen, haben wir eine dedizierte C-Bibliothek entwickelt. Diese Bibliothek abstrahiert die komplexen Hardware-Zugriffe über das OBI-Interface und stellt dem Entwickler eine einfache und intuitive API zur Verfügung.

## Architektur der Bibliothek
Die C-Bibliothek basiert auf dem Prinzip des Memory-Mapped I/O (MMIO). Der Hardware-Cache ist in den Adressraum des Prozessors eingeblendet. In der Bibliothek haben wir Zeiger auf die spezifischen Basisadressen der Cache-Register (für Key, Value Low/High und Operation/Control) definiert. Die Basisadresse `REDIS_CACHE_BASE_ADDR` wird dabei zentral in der `config.h` konfiguriert.

## Kernfunktionen
Die API bietet Funktionen für die grundlegenden Cache-Operationen und gibt jeweils einen Statuscode (`REDIS_CACHE_STATUS_OK`, `REDIS_CACHE_STATUS_MISS` oder `REDIS_CACHE_STATUS_ERR`) zurück:

- `redis_cache_get(key, &value_out)`: Schreibt den Schlüssel in das Key-Register, löst die GET-Operation aus und wartet auf den Abschluss. Bei einem Hit wird der 64-Bit Wert aus den Value-Registern gelesen und in `value_out` gespeichert.
- `redis_cache_upsert(key, value)`: Schreibt den 64-Bit Wert in die Value-Register, den Schlüssel in das Key-Register und triggert die UPSERT-Operation im Operations-Register.
- `redis_cache_delete(key)`: Übergibt den Schlüssel und startet die DELETE-Operation.

### Beispiel: Werte schreiben und lesen

```c
#include "redis_cache.h"

uint32_t key = 0x11111111u;
uint64_t value = 0x1122334455667788ULL;

// Wert in den Cache schreiben
int status = redis_cache_upsert(key, value);
if (status != REDIS_CACHE_STATUS_OK) {
    // Fehlerbehandlung: Schreiben fehlgeschlagen
    return -1;
}

// Wert aus dem Cache lesen
uint64_t read_value = 0;
status = redis_cache_get(key, &read_value);
if (status == REDIS_CACHE_STATUS_ERR) {
    // Fehlerbehandlung: Hardware-Fehler oder Timeout
    return -1;
} else if (status == REDIS_CACHE_STATUS_MISS) {
    // Schlüssel nicht im Cache gefunden, z.B. Standardwert setzen
    read_value = 0;
}

// read_value enthält nun 0x1122334455667788ULL (oder 0 bei Miss)
```

## Einbindung in Croc
Wir haben die C-Bibliothek so konzipiert, dass sie nahtlos in das Software-Ökosystem des CROC SoCs integriert werden kann. Sie wird als statische Bibliothek kompiliert und gegen die Anwendungssoftware gelinkt. Durch die Verwendung von standardisierten Datentypen und einer klaren Trennung von Hardware-spezifischen Adressen (die über Header-Dateien konfiguriert werden) ist die Bibliothek portabel und leicht anpassbar.

