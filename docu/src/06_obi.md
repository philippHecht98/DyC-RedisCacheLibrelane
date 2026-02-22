# OBI

## OBI Protokoll

## Register

Das OBI Protokoll wird genutzt um Daten in Register zu schreiben und daraus auszulesen.
Standardmäßig sind folgende Register vorhanden:


|        | Value    | Key | Ctrl |
| ------ | -------- | ---------- | ------------ |
| Größe  | 64 (8 Bytes) | 32 (4 Bytes) | 32 (4 Bytes)           |
| Offset | 0        | 8          | 12            |

Die Größe der Register ist in der cache_cfg_pkg. Die Offset Werte leiten sich aus den den Größen der Key und Value Register ab.
In den OBI Nachrichten wird das Offset (addr) mitgegeben. Anhand des Offsets können Daten in das richtige Register geschrieben werden.

## OBI Request

Die OBI Request wird von dem Master an den Slave (Interface) verserndet. Die 72 Bit lange Nachricht setzt sich aus dem  Adress-Channel und dem Kontrollsignal zusammen.

| Feld in obi_req_t | Bit-Breite    | Beschreibung |
| ---------         | ----------    | ------------ |
| addr              | 32            | Register Speicheradresse: Der Wert entspricht dem Offset um die übermittelten Daten in dem richtige Register zuzuweisen|
| we                | 1             | Write Enable: 1 bedeutet Schreiben, 0 bedeutet Lesen.|
| be                | 4             | Byte Enable: Gibt an, welche Bytes der 32-Bit-Daten (wdata) gültig sind. Für ein volles 32-Bit-Wort ist das 1111 |
| wdata             | 32            | Write Data: Die Daten, die in den Speicher/das Register geschrieben werden sollen. |
| aid               | 1             | Address ID: Eine ID für die Transaktion |
| a                 | 1             | Optional: Ein optionales Signal des OBI-Standards (in der Minimal-Konfiguration 1 Bit groß). |
| req               | 1             | Request: Das Handshake-Signal. Wenn 1, bittet der Master um eine Transaktion. |


## OBI Response

Die OBI Response wird von dem Slave (Interface) an den Master versendet. Die 37 Bit lange Nachricht setzt sich aus dem R-Channel, dem Grant un dem Valid Signalen zusammen.

| Feld in obi_rsp_t | Bit-Breite    | Beschreibung |
| ---------         | ----------    | ------------ |
| rdata             | 32            | Read Data: Die Daten, die vom Interface gelesen wurden |
| rid               | 1             | Response ID: Spiegelt die aid aus dem Request wider, um Antworten zuzuordnen |
| err               | 1             | Error: Wird 1, falls beim Zugriff ein Fehler aufgetreten ist (z. B. falsche Adresse). |
| r                 | 1             | Optional: Ein optionales Signal für die Response (in der Minimal-Konfiguration 1 Bit). |
| gnt               | 1             | Grant: Handshake-Signal. Der Slave setzt dieses Bit auf 1, um zu signalisieren: "Ich habe deinen Request (req=1) akzeptiert und verarbeite ihn" |
| rvalid            | 1             | Response Valid: Wird 1, wenn die zurückgegebenen Daten in r.rdata gültig sind. |