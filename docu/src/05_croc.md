# CROC

Ausarbeitung Luca Pinnekamp

Das CROC (Custom RISC-V Open-source Core) System-on-Chip (SoC) dient als Zielplattform für die Integration unseres Hardware-Redis-Caches. Wir haben uns für diese Plattform entschieden, da sie die notwendige Infrastruktur bietet, um unsere Erweiterung in einem realistischen System zu evaluieren.

## CROC Architektur

![CROC SoC Architektur](../img/croc_arch.svg){ width=75% }

Die Architektur des CROC SoCs ist hierarchisch in verschiedene Domänen unterteilt, um eine klare Trennung zwischen dem Kernsystem und benutzerdefinierten Erweiterungen zu gewährleisten:

- **croc_soc**: Die oberste Ebene des Systems, die alle Subsysteme und externen Schnittstellen zusammenfasst.
- **croc_domain**: Beinhaltet den eigentlichen RISC-V Prozessorkern, den primären Speicher sowie grundlegende Peripheriegeräte (UART, Timer, etc.).
- **user_domain**: Ein dedizierter Bereich für benutzerdefinierte Hardware. Dieser Bereich ist über einen OBI Bus an die `croc_domain` angebunden. Hier haben wir unseren Redis Cache integriert.

## Implementation bei uns im Projekt

Um den Redis Cache in das CROC SoC zu integrieren, mussten wir spezifische Anpassungen in der `user_domain` und den zugehörigen Konfigurations-Packages vornehmen. Diese waren nötig um unseren OBI Subordinate an den bestehenden OBI Crossbar anzuschließen.

### Anpassungen im `user_pkg`
Das `user_pkg` definiert die Speicherarchitektur und die Adressräume der benutzerdefinierten Peripherie. Folgende Änderungen haben wir hier vorgenommen:

1. **Adressraum-Definition**: Wir haben dem Redis Cache einen festen Adressbereich im Memory Map des SoCs zugewiesen. Dazu definierten wir eine Basisadresse (`UserRedisCacheAddrOffset`) und die Größe des Adressraums (`UserRedisCacheAddrRange`).
2. **Erweiterung der Peripherie-Anzahl**: Wir haben die Konstante für die Anzahl der Subordinates im User-Interconnect (`NumUserDomainSubordinates`) erhöht, um den neuen IP-Core aufnehmen zu können.
3. **Adress-Dekodierung**: Die Adress-Dekodierungsregeln (`user_addr_map`) für den Crossbar haben wir um den Bereich des Redis Caches erweitert, damit Speicherzugriffe des Prozessors korrekt an unseren IP-Core geroutet werden.

```systemverilog
  localparam bit [31:0] UserRedisCacheAddrOffset = UserRomAddrOffset + UserRomAddrRange;
  localparam bit [31:0] UserRedisCacheAddrRange  = 32'h0000_1000;

  // Address rules given to address decoder
  localparam croc_pkg::addr_map_rule_t [NumDemuxSbrRules-1:0] user_addr_map = '{
    // 1: ROM
    '{ idx: UserRom, 
       start_addr: UserRomAddrOffset, 
       end_addr: UserRomAddrOffset + UserRomAddrRange }, 
    // 2: RedisCache
    '{ idx: UserRedisCache, 
       start_addr: UserRedisCacheAddrOffset, 
       end_addr: UserRedisCacheAddrOffset + UserRedisCacheAddrRange }
  };
```

### Anpassungen in der `user_domain`
In der `user_domain` erfolgt die eigentliche Instanziierung und Verdrahtung der Hardware-Module. Hierbei wird der Redis Cache als Subordinate in den OBI-Bus eingehängt:

1. **Signal-Deklaration**: Zunächst haben wir die OBI-Request- und Response-Signale (`user_redis_cache_obi_req`, `user_redis_cache_obi_rsp`) für den Cache deklariert und mit dem Demultiplexer (`all_user_sbr_obi_req`, `all_user_sbr_obi_rsp`) verbunden.
2. **Instanziierung des Redis Cache**: Anschließend haben wir das Top-Level-Modul unseres Redis Caches in der `user_domain` instanziiert.
3. **OBI-Parameter**: Um eine korrekte implementation des OBI Interface zu ermöglichen werden hier die vom croc SOC definierten Parameter für die `ObiCfg`, `obi_req_t` und `obi_rsp_t` übergeben um als Datentypen bzw. für die Konfiguration der korrekten Busbreite im Redis Cache verwendet zu werden.
4. **OBI-Schnittstellen-Verbindung**: Die zuvor deklarierten OBI-Signale haben wir an die entsprechenden Ports des Caches angeschlossen.

```systemverilog
  // OBI bus to RedisCache
  sbr_obi_req_t user_redis_cache_obi_req;
  sbr_obi_rsp_t user_redis_cache_obi_rsp;

  // Fanout into more readable signals
  assign user_redis_cache_obi_req             = all_user_sbr_obi_req[UserRedisCache];
  assign all_user_sbr_obi_rsp[UserRedisCache] = user_redis_cache_obi_rsp;

  // ... (Demultiplexer Logik) ...

  // RedisCache Subordinate
  redis_cache #(
    .ObiCfg      ( SbrObiCfg     ),
    .obi_req_t   ( sbr_obi_req_t ),
    .obi_rsp_t   ( sbr_obi_rsp_t )
  ) i_user_redis_cache (
    .clk (clk_i),
    .rst_n (rst_ni),
    .obi_req_i  ( user_redis_cache_obi_req ),
    .obi_resp_o  ( user_redis_cache_obi_rsp )
  );
```

Durch diese strukturierte Integration ist der Redis Cache nun als Memory-Mapped I/O (MMIO) Gerät für den RISC-V Prozessor sichtbar und kann über die von uns entwickelte C-Bibliothek angesteuert werden.