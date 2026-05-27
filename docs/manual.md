# KOMMENTATORKIT — TEKNISK MANUAL

**Oppsett | Tilkobling | Programvare | Vedlikehold og Feilsøking**

Versjon 2.1 | Mai 2026 | Intern / Teknisk  
Kun for internt bruk av NEP teknisk personell.

---

## 1. SYSTEMOVERSIKT

NEP Kommentatorkit er et selvforsynt, mobilt system for distribusjon av video og lyd til kommentatorbokser under sportsarrangementer. Systemet leverer videosignaler (PGM, CIS, TV2-retur m.fl.) til opptil 10 kommentatorbokser og styres via Bitfocus Companion på Raspberry Pi med Elgato Stream Deck-kontrollpaneler.

| Komponent | Funksjon |
|---|---|
| BMD Videohub 20x20 | Hoved-videorouter — styrer alle inn/ut-signaler via BNC |
| Slate 7 Router (GL.iNet) | Nettverksruter for kit-nettverket (WAN/LAN) |
| HPE Nettverksswitch | Kobler alle Raspberry Pi-er og videorouter i ett lokalt nett |
| Companion Pi — 192.168.8.101 | Kjører Bitfocus Companion — hoved-kontroller for alle Stream Decks |
| Satelitt Pi #1 — 192.168.8.102 | Raspberry Pi 5 med companion satellite og Stream Deck XL |
| Satelitt Pi #2 — 192.168.8.103 | Raspberry Pi 5 med companion satellite og Stream Deck XL |
| Satelitt Pi #3 — 192.168.8.104 | Raspberry Pi 5 med companion satellite og Stream Deck XL |
| Satelitt Pi #4 — 192.168.8.105 | Raspberry Pi 5 med companion satellite og Stream Deck XL |
| Satelitt Pi #5 — 192.168.8.106 | Raspberry Pi 5 med companion satellite og Stream Deck XL |
| Satelitt Pi #6 — 192.168.8.107 | Raspberry Pi 5 med companion satellite og Stream Deck XL |
| Strømpadde | Strømfordeling til hele racket |

---

## 2. RACK-OVERSIKT OG KOMPONENTER

Racket er bygd opp med fremside og bakside. Alle porter er merket med kabelnummer.

### FREMSIDE

| Posisjon | Komponent | Notat |
|---|---|---|
| 1 | Slate 7 Router + Companion Pi | Delt 1U-panel |
| 2 | BMD Videohub 20x20 | Hoved-videorouter med frontpanel-display |
| 3 | 1U blindpanel med brush | Kabelgjennomføring |
| 4 | Nettverksswitch (HPE) | Alle nettverkstilkoblinger — 24 porter |
| 5 | Blindpanel | |

### BAKSIDE

Baksiden har to rader med BNC-kontakter. Øvre rad: Router IN (porter 1–10) og CAT-patch samt strøminput. Nedre rad: Router OUT (porter 1–20). Se kabeloversikten (seksjon 6) for komplett kartlegging.

> ⚠️ **ADVARSEL:** Strøm skal alltid kobles til sist og fra først. Kontroller at alle kabler er festet før du skrur på rack.

---

## 3. NETTVERKS- OG IP-KONFIGURASJON

Alle enheter opererer på subnett 192.168.8.x. Tabellen under viser faste IP-adresser.

| IP-adresse | Enhet | Switch-port |
|---|---|---|
| 192.168.8.50 | BMD Videohub | Port 23 |
| 192.168.8.101 | Companion Pi (Host) | Port 21 |
| 192.168.8.102 | Satelitt Pi #1 | |
| 192.168.8.103 | Satelitt Pi #2 | |
| 192.168.8.104 | Satelitt Pi #3 | |
| 192.168.8.105 | Satelitt Pi #4 | |
| 192.168.8.106 | Satelitt Pi #5 | |
| 192.168.8.107 | Satelitt Pi #6 | |
| 192.168.8.115 | HPE Switch (management) | — |

> ✅ **TIPS:** WAN plugges på port 2 på nettverksswitch og går videre til Slate 7 WAN på port 1.

> ℹ️ **MERK:** Companion webgrensesnitt: `http://192.168.8.101:8000` — tilgjengelig fra alle enheter på nettverket.

> ℹ️ **MERK:** NEP Satellite Dashboard: `http://192.168.8.101:8080` — se seksjon 9.

> ℹ️ **MERK:** SSH-innlogging: Brukernavn: `pi` | Passord: `password`

---

## 4. TILKOBLING — FYSISK OPPSETT

Systemet bruker en stjernetopologi der Companion Pi er sentrum. 6 Satelitt Pi-er kobles via nettverksswitchen eller via internett og VPN. Hver Satelitt Pi betjener en kommentatorboks.

### Tilkoblingsrekkefølge ved rigg

1. Plasser racket på riggeposisjon og sikre det mot velting.
2. Koble strøm-input til strømpadden (bakside, øvre høyre hjørne).
3. Trekk CAT-kabler fra Companion Pi til Satelitt Pi-er via switch.
4. Koble videokilder (PGM, CIS 1/2/3, TV2-retur, Kamera 1) til BMD Router IN 1–6 via BNC.
5. Koble BMD Router OUT til respektive kommentatorboks-monitorer via BNC.
6. Verifiser tilkobling på Connections-siden i Companion (grønn = online).
7. Koble Satelitt Pi-er til kit via LAN eller vanlig internett.

---

## 5. INN- OG UTGANGER — BMD VIDEOHUB 20x20

BMD Videohub 20x20 har 20 innganger og 20 utganger. Routing styres via Companion (Admin Panel → Video Router) eller via kommentatorpanelene.

### INNGANGER

| Input nr. | Signal / Kilde |
|---|---|
| 1 | PGM (Programbilde) |
| 2 | CIS 1 |
| 3 | CIS 2 |
| 4 | CIS 3 |
| 5 | TV2 Retur |
| 6 | Kamera 1 |
| 7–20 | Future Use |

### UTGANGER

| Output nr. | Destinasjon |
|---|---|
| 1 | Komboks 1 — Monitor Høyre |
| 2 | Komboks 1 — Monitor Senter |
| 3 | Komboks 1 — Monitor Venstre |
| 4 | Komboks 2 — Monitor Høyre |
| 5 | Komboks 2 — Monitor Venstre |
| 6 | Komboks 3 — Monitor Høyre |
| 7 | Komboks 3 — Monitor Venstre |
| 8 | Komboks 4 — Monitor Høyre |
| 9 | Komboks 4 — Monitor Venstre |
| 10 | Komboks 5 — Monitor Høyre |
| 11 | Komboks 5 — Monitor Venstre |
| 12 | Komboks 6 — Monitor Høyre |
| 13 | Komboks 6 — Monitor Venstre |
| 14–18 | Ikke konfigurert |
| 19 | LED (styres via LED-velger i Companion) |
| 20 | NRK |

> ℹ️ **MERK:** Endring av navn på innganger/utganger gjøres via Blackmagic Videohub Setup programvare.

---

## 6. KABELOVERSIKT

Alle kabler er merket med kabelnummer (001–033). Bruk alltid kabelnummer ved feilsøking.

| Kabel nr. | Beskrivelse | Notat |
|---|---|---|
| 001 | BMD In 1 | PGM-innsignal |
| 002 | BMD In 2 | CIS 1 |
| 003 | BMD In 3 | CIS 2 |
| 004 | BMD In 4 | CIS 3 |
| 005 | BMD In 5 | TV2 Retur |
| 006 | BMD Out 1 | Komboks 1 Mon Høyre |
| 007 | BMD Out 2 | Komboks 1 Mon Senter |
| 008 | BMD Out 3 | Komboks 1 Mon Venstre |
| 009 | BMD Out 4 | Komboks 2 Mon Høyre |
| 010 | BMD Out 5 | Komboks 2 Mon Venstre |
| 011 | BMD Out 6 | Komboks 3 Mon Høyre |
| 012 | BMD Out 7 | Komboks 3 Mon Venstre |
| 013 | BMD Out 8 | Komboks 4 Mon Høyre |
| 014 | BMD Out 9 | Komboks 4 Mon Venstre |
| 015 | BMD Out 10 | Komboks 5 Mon Høyre |
| 016 | BMD Out 11 | Komboks 5 Mon Venstre |
| 017 | BMD Out 12 | Komboks 6 Mon Høyre |
| 018 | BMD Out 13 | Komboks 6 Mon Venstre |
| 019–025 | BMD Out 14–20 | Analyse / LED / NRK |
| 026 | CAT Patch 1 | Switch Port 9 |
| 027 | CAT Patch 2 | Switch Port 11 |
| 028 | CAT Patch 3 | Switch Port 13 |
| 029 | CAT Patch 4 | Switch Port 12 |
| 030 | Router WAN | Switch Port 1 |
| 031 | Router LAN | Switch Port 10 |
| 032 | VideoHub LAN | Switch Port 23 |
| 033 | Companion Pi LAN | Switch Port 21 |

---

## 7. COMPANION / STREAM DECK — PROGRAMVARE

Bitfocus Companion kjører på Companion Pi (`192.168.8.101:8000`) og styrer alle Stream Deck-paneler via Satelitt Pi-ene.

### 7.1 Startside — kommentatorvalg

Startsiden vises når Stream Deck starter. NEP-logo i alle fire hjørner fungerer som LOCK-knapp for tilgang til admin-funksjoner.

**Knapper på startsiden:**
- **Kom 1 – Kom 6** (rad 2): Trykk for å navigere inn på aktuell komboks-side.
- **Kom 7 – Kom 10** (rad 3): Ekstra boksknapper ved behov (krever konfigurering av videohub-destinasjoner).
- **NEP-logo (alle hjørner):** LOCK-knapp — se seksjon 7.2 for bruk.

> ✅ **TIPS:** Rask tilbakestilling av alle bokser: Hold inne LOCK-knappen (NEP-logo øverst til VENSTRE) og trykk deretter NEP-logo øverst til HØYRE. Da settes alle kombokser tilbake til standard.

### 7.2 Admin Panel

Admin Panel er tilgjengelig kun for teknisk personell og er skjult bak en dobbel lock-sekvens.

**Slik åpner du Admin Panel:**
1. Hold inne NEP-logo øverst til VENSTRE (LOCK-knapp).
2. Hold inne NEP-logo nederst til VENSTRE i ca. 2 sekunder — Admin Panel åpnes.
3. Snarvei: Hold LOCK og trykk på ønsket komboks-knapp for direkteaksess til kanalvelger.

| Knapp i Admin Panel | Funksjon |
|---|---|
| Ruter | Åpner ruting-panelet — ett panel med alle inn- og utganger på BMD Videohub |
| Kanal Velger | Åpner kanalvelger-siden for å tilordne TV-kanal til kombinatorboksene |
| Slack | Åpner/viser Slack-integrasjon og BlyvisBot-status |
| Lys | Styrer lysoppsett for kommentatorboksene |
| Connections | Status på alle Pi-er og connections. Mulighet for å aktivere/deaktivere tilkoblinger |
| SpeedTest | Kjører nettverkshastighetsttest fra Companion Pi |
| Salvos | Lagrede ruting-presets — kjør hele ruteoppsett med ett trykk |
| Back | Tilbake til hovedpanelet |

### 7.3 Connections-side

Viser sanntidsstatus for alle connections og Pi-er. Grønn = online, svart/grått = deaktivert, rød = offline.

| Knapp | Farge | Betyr |
|---|---|---|
| Pi #1–#4 | Grønn | Satelitt Pi er online og tilgjengelig |
| Pi #5–#6 | Svart/grått | Satelitt Pi er offline eller ikke tilkoblet |
| Switch Online | Grønn | HPE Switch er tilgjengelig |
| Connected to internet | Grønn | Internettilgang tilgjengelig via Slate 7 |
| Videohub | Grønn/grått | BMD Videohub tilkoblet / ikke tilkoblet |
| Slack | Grønn/grått | Slack-integrasjon tilkoblet / frakoblet |

> ⚠️ **ADVARSEL:** Hvis en Satelitt Pi vises som offline, vil Stream Deck-en i tilhørende komboks ikke fungere. Se seksjon 10 for feilsøking.

### 7.4 Kanalvelger

Kanalvelgeren tilordner TV-kanal til en komboks. Valget endrer logoen på Stream Deck og kanalnavnet i BlyvisBot-meldinger.

**Slik endrer du kanal:**
- **Metode A:** Admin Panel → Kanal Velger → velg boks → velg kanal.
- **Metode B (snarvei):** Hold LOCK + trykk ønsket komboks-knapp → direkteaksess til kanalvelger.
- **Tilbakestill alle:** Hold LOCK (venstre) + trykk NEP-logo (høyre).

| Kategori | Kanaler |
|---|---|
| NEP (standard) | Standard — brukes når ingen spesifikk kanal er tildelt |
| AlterEgo | AlterEgo |
| CBS | CBS |
| TV2 | TV2 Norge |
| Cenera | Cenera |
| C+ | Polen / Frankrike |
| 3CAT | 3CAT |
| Viaplay | Finland / Nederland / Sverige / Danmark / Norge |
| UEFA | UEFA |
| ESPN | Brasil |
| Prime Video | Italia |
| ZDF | ZDF |
| TNT Sports | UK / Mexico / Chile / Brasil |

### 7.5 Komboks-side

Det kommentatoren ser på sin Stream Deck.

| Knapp | Farge | Funksjon |
|---|---|---|
| Help | Rød | Sender hjelpevarsel til Slack (#kommentatorstøtte) via BlyvisBot |
| Help (bekreft) | Rød → grønn | Tekniker bekrefter hjelp mottatt |
| Request Coffee | Hvit | Sender kaffeforespørsel til Slack |
| PGM | Hvit | Velger PGM-signal — gul = aktiv rute |
| CIS 1 / CIS 2 / CIS 3 | Hvit | Velger CIS-statistikksignal |
| TV2 Retur | Hvit | Velger TV2 Retur-signal |
| Kamera 1 | Hvit | Velger Kamera 1-signal |
| in 7 / in 8 | Hvit | Offside Venstre / Offside Høyre |
| Kanallogo (hjørner) | Hvit | Hold 2 sek for å gå tilbake til kanalvelger |

> ℹ️ **MERK:** Gul knapp = aktiv rute. Kun én rute kan være aktiv om gangen per monitor.

### 7.6 LED-velger

Styrer videosignalet til LED-teknikerens skjerm (output 19 på BMD Videohub).

**Slik åpner du LED-velgeren:**
1. Hold inne kanallogoen (NEP-logo) nederst til HØYRE på komboksvelger-siden.
2. LED-velgersiden åpnes — velg ønsket signal for output 19.

### 7.7 BlyvisBot — varslingssystem via Slack

BlyvisBot poster automatiske meldinger til `#kommentatorstøtte` basert på knapptrykk i Companion.

| Handling | Slack-melding | Emoji |
|---|---|---|
| Help-knapp trykkes | [Kanalnavn] Trenger Hjelp | 🔴 |
| Hjelp bekreftet (tekniker) | [Kanalnavn] har fått hjelp | ✅ |
| Request Coffee trykkes | [Kanalnavn] Trenger Kaffe | ☕ |
| Kaffe levert (tekniker) | [Kanalnavn] Har fått kaffe | ☕ |

---

## 8. NEP AUTOMATIKK — TAILSCALE FAILOVER OG WATCHDOG

Dette er NEP-spesifikke tjenester som kjører i bakgrunnen på alle Satelitt Pi-er. De sikrer at Pi-ene alltid er koblet til Companion, og gjenoppretter tilkobling automatisk ved feil.

### 8.1 Tailscale Failover

Satelitt Pi-ene kan koble til Companion via to veier:

| Rute | Betingelse |
|---|---|
| **LAN** (192.168.8.x) | Primær — brukes alltid når Pi er på kit-nettverket |
| **Tailscale VPN** | Backup — brukes automatisk når LAN ikke er tilgjengelig |

Failover-scriptet (`nep-ts-failover.sh`) kjører hvert 5. sekund og bytter automatisk mellom LAN og Tailscale. Du kan også tvinge en bestemt rute manuelt via dashbordet (Auto / LAN / Tailscale-knapper på hvert Pi-kort).

### 8.2 Satellite Watchdog

Watchdog-tjenesten (`nep-satellite-watchdog.service`) overvåker satellite-prosessen og starter den automatisk på nytt hvis den henger i «reconnecting»-tilstand. Dette løser problemet der Stream Deck viser «Connected» men Companion-knappene ikke virker.

### 8.3 NEP Modus — deaktiver for annen produksjon

Hvis en Satelitt Pi skal brukes med en **annen** Companion (ikke kit-companion på 192.168.8.101), må NEP-automatikken deaktiveres slik at failover og watchdog ikke forstyrrer.

**Metode 1 — Fra dashbordet:**
Finn Pi-kortet → trykk **[Deaktiver]** ved «NEP Modus» i System-seksjonen.

**Metode 2 — Direkte fra Pi (fra nettleser):**
Åpne i nettleser: `http://[Pi-IP]:8080/mode`  
Trykk **✗ Deaktiver NEP Modus** — gjelder persistent over reboot.  
Trykk **✓ Aktiver NEP Modus** for å gjenopprette normal drift.

> ℹ️ **MERK:** Deaktivering maskerer tjenestene — de starter ikke opp igjen selv etter reboot, inntil du aktiverer dem igjen.

---

## 9. NEP SATELLITE DASHBOARD

Dashbordet gir sanntidsoversikt over alle Pi-er og enheter på kit-nettverket. Det kjører på Companion Pi og er tilgjengelig fra alle enheter på nettverket.

**Adresse:** `http://192.168.8.101:8080`

### 9.1 Statuskort per Pi

Hvert Pi-kort viser:

| Felt | Beskrivelse |
|---|---|
| Statusindikator | Grønn = online via LAN, Lilla = online via Tailscale, Oransje = satellite frakoblet, Rød = offline |
| Satellite | ✓ Tilkoblet / ✗ Frakoblet — viser om companion satellite er aktiv |
| Rute | LAN eller Tailscale — hvilken vei trafikken går |
| Failover-teller | Antall ganger failover har byttet rute |
| CPU-temp | Temperatur på Pi-prosessoren |
| Versjon | Versjon av health.py som kjører |
| Watchdog | ✓ Aktiv / ✗ Ikke installert |
| NEP Modus | ✓ Aktiv / ✗ Av — se seksjon 8.3 |

### 9.2 Route-toggle per Pi

På hvert kort kan du manuelt velge rute:
- **Auto** — scriptet velger automatisk (anbefalt)
- **LAN** — tving LAN alltid
- **Tailscale** — tving Tailscale alltid

### 9.3 Oppdater alle Pi-er

Trykk **⬆ Oppdater alle** i topmenyen for å sende ny programvare til alle Pi-er samtidig.

- Oppdaterer: `health.py`, dashboard, watchdog, failover-script, diagnose-script
- Rører **ikke**: Tailscale, satellite, satellite-config, nettverksregler
- Viser fremdrift per Pi — grønn hake når ferdig

### 9.4 Diagnose

Trykk **🔍 Diagnose** på et Pi-kort for å laste ned en komplett loggfil fra den Pi-en. Filen inneholder:
- Status på alle NEP-tjenester
- Satellite-logger (siste 200 linjer)
- Failover- og watchdog-logger
- Nettverkskonfigurasjon
- Health API-respons

> ✅ **TIPS:** Send loggfilen til Joakim for rask feilsøking på avstand.

**Alternativt — kjør diagnose direkte på Pi via SSH:**
```bash
curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/scripts/nep-diagnose.sh | bash
```
Filen lagres i `/tmp/nep-diag-TIMESTAMP.txt`.

### 9.5 Administrer Pi-er og enheter

Trykk **Administrer** for å legge til, redigere eller slette enheter fra dashbordet. Du kan legge til:
- **Pi** — Satelitt Pi med LAN- og Tailscale-IP
- **Switch, Ruter, Videohub, Annen enhet** — overvåkes med ping

### 9.6 Varsler (Pushover)

Trykk **🔔 Varsler** i topmenyen for å konfigurere Pushover-varsler.

| Felt | Beskrivelse |
|---|---|
| App Token | Pushover applikasjonsnøkkel |
| User Key | Pushover brukernøkkel |
| Varsler aktivert | Master-toggle — slår av/på alle varsler |
| Send testmelding | Sender en testmelding for å verifisere oppsettet |

**Varseltyper (per type hendelse):**

| Toggle | Hendelse |
|---|---|
| 🔴 Pi går offline | Enhet er ikke lenger nåbar |
| ✅ Pi online igjen | Enhet er tilbake etter bortfall |
| ⚠️ Satellite frakoblet | Companion satellite mistet tilkobling |
| ✅ Satellite tilkoblet igjen | Satellite reconnectet |
| 🌡️ Høy temperatur | Pi overskrider temp-grense |
| ⚡ Byttet til Tailscale | Pi mistet LAN og kjører via VPN |
| ✅ Tilbake på LAN | Pi er tilbake på lokalt nett |

**Per-enhet toggles:**  
Nederst i varslingssiden vises alle enheter fra dashbordet. Du kan skru av/på varsler individuelt per enhet — nyttig hvis en switch er kjent ustabil men du ikke vil ha varsel for den.

**Temperaturgrenser:**
- **Varsel over** — send varsel når Pi når denne temperaturen (standard: 75°C)
- **OK under** — send «temp normal»-varsel når Pi faller under denne (standard: 65°C)

> ℹ️ **MERK:** Innstillingene lagres på Companion Pi i `/home/pi/health/notifications-config.json` og leses av watchdog-tjenesten umiddelbart uten restart.

### 9.7 Kollapserbare kort og seksjoner

For å spare skjermplass kan alt på dashbordet kollapsas:

- **Pi-kort** — klikk på korthodet (toppen med navn og statusindikator) for å skjule/vise hele innholdet
- **Seksjoner** — klikk på seksjonsoverskriften (Companion / Nettverk / Failover / System) for å kollapse den seksjonen på alle Pi-kort samtidig
- **Device-kort** (Switch, Videohub osv.) — klikk hvor som helst på kortet for å kollapse til minimal visning

Alle kollapsevalg huskes automatisk i nettleseren til neste gang.

### 9.8 Produksjonsvelger

🎬-knappen i topbaren lar deg lagre ulike **produksjoner** — hver produksjon husker sin egen liste med enheter som overvåkes. Nyttig når du bruker det samme kitet til forskjellige oppdrag med ulike enheter.

**Slik bruker du produksjonsvelgeren:**

| Handling | Beskrivelse |
|---|---|
| Klikk 🎬-knappen | Åpner dropdown med alle produksjoner — aktiv produksjon er merket med ✓ |
| Velg en produksjon | Dashbordet bytter til den produksjonens enhetsliste umiddelbart |
| ＋ Ny produksjon | Oppretter en ny produksjon og lagrer de nåværende enhetene i den |
| ⚙ Administrer produksjoner | Åpner oversikt — gi nytt navn, aktiver eller slett produksjoner |

> ℹ️ **MERK:** Produksjoner lagres på Companion Pi i `/home/pi/health/productions.json`. Minst én produksjon må alltid finnes — siste produksjon kan ikke slettes.

> ✅ **TIPS:** Lag én produksjon per venue eller oppdragstype (f.eks. «Bodø», «Oslo», «Test-rigg») og bytt enkelt mellom dem når du rigger opp.

---

## 10. VEDLIKEHOLD OG OPPDATERING

### Oppdater alle Pi-er (anbefalt metode)

1. Åpne dashbordet: `http://192.168.8.101:8080`
2. Trykk **⬆ Oppdater alle**
3. Vent til alle Pi-er viser ✓ Ferdig (ca. 30–60 sek per Pi)

### Installer ny Satelitt Pi

```bash
curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install.sh | bash
```

Velg Pi-nummer (1–6) når du blir spurt. Scriptet installerer:
- Health API (port 8080)
- Tailscale failover
- Satellite watchdog
- Diagnose-script
- Tailscale (hvis ikke installert)

**Etter installasjon — koble til Tailscale (kun første gang):**
```bash
sudo tailscale up
```

### Companion Pi — Database i RAM (ytelsesoptimalisering)

Companion lagrer sin database (~80 MB) og tar periodisk backup. På SD-kort blokkerte dette Node.js event loop i 3–6 sekunder, noe som fikk alle satelitt-Pi-er til å droppe tilkoblingen samtidig.

**Løsning installert på Companion Pi:**
- Companion-databasen kjører fra RAM (tmpfs) istedenfor SD-kort/USB
- Synkroniseres til USB-disken hvert 5. minutt automatisk
- Backup-tid: fra ~5800 ms → under 50 ms

**USB-disk:** Samsung FIT Plus 64 GB — montert på `/home/companion`  
**RAM-database:** Montert på `/home/companion/.config/companion-nodejs/v4.3`

**Verifiser at fiksen fungerer:**
```bash
journalctl -u companion --since "1 hour ago" | grep "backup complete"
# Skal vise: "backup complete in XXms" — forventet under 100 ms
```

**Sjekk status på RAM-database-tjenestene:**
```bash
systemctl status companion-ramdb companion-ramdb-sync.timer
```

**Manuell sync til USB (f.eks. før planlagt strømstans):**
```bash
sudo /usr/local/sbin/companion-ramdb-sync.sh
```

> ⚠️ **VIKTIG:** Ved uplanlagt strømstans på Companion Pi kan maksimalt 5 minutter med konfigurasjonsendringer gå tapt. Companion-databasen synkes automatisk hvert 5. minutt, og ved normal nedstengning synkes den alltid til USB.

### Installer Health API på Companion Pi (uten satellite)

```bash
curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install-health.sh | bash
```

### Nyttige kommandoer

| Handling | Kommando |
|---|---|
| Se failover-logg live | `journalctl -t nep-ts-failover -f` |
| Se watchdog-logg | `journalctl -t nep-satellite-watchdog -n 50` |
| Restart satellite | `sudo systemctl restart satellite` |
| Status alle NEP-tjenester | `systemctl status nep-health satellite nep-ts-failover.timer nep-satellite-watchdog` |
| Endre Pi-navn | `sudo nano /etc/systemd/system/nep-health.service` → endre `NEP_ID=...` → `sudo systemctl daemon-reload && sudo systemctl restart nep-health` |
| Sett tidssone | `sudo timedatectl set-timezone Europe/Oslo` |
| Aktiver SSH på SD-kort (Mac) | `touch /Volumes/bootfs/ssh` |

---

## 11. FEILSØKING

### Sjekkliste før sending

- [ ] Alle Pi-er grønne i dashbordet (`http://192.168.8.101:8080`)
- [ ] Companion tilgjengelig på `http://192.168.8.101:8000`
- [ ] BMD Videohub tilkoblet (grønn på Connections-siden)
- [ ] Test minst ett Stream Deck — navigering og signalvalg fungerer
- [ ] BlyvisBot svarer i Slack (`#kommentatorstøtte`)
- [ ] Korrekt kanal tilordnet hver kommentatorboks

### Sjekkliste etter sending / nedrigg

- [ ] Koble fra alle Stream Decks (USB) før strøm kobles fra rack
- [ ] Koble fra alle BNC-kabler og rull opp forsiktig
- [ ] Koble fra CAT-kabler
- [ ] Koble fra strøm
- [ ] Legg utstyr tilbake i kassen med eventuelle USB-C strømforsyninger

> ⚠️ **HUSK:** Strømkabel til kommentatorkit legges i lokket.

### Feilsøkingstabell

| Feilsymptom | Tiltak |
|---|---|
| Stream Deck svarer ikke | Koble USB fra og til. Sjekk dashbordet — restart aktuell Pi. |
| Companion ikke tilgjengelig | Restart Pi eller SSH inn og kjør restart-kommando (se under). |
| Ingen video i komboks | Sjekk BMD-routing i Admin Panel → Video Route. Sjekk BNC-kabler. |
| BlyvisBot sender ikke | Sjekk nettverkstilkobling og Slack-integrasjon i Connections-siden. |
| Pi offline i dashbordet | Hard reset: koble strøm fra Pi i 10 sek, koble til igjen. Vent 90 sek. |
| Feil kanal/logo på boks | Hold LOCK + trykk komboks-knapp → kanalvelger → velg kanal. |
| Alle bokser feil kanal | Hold LOCK (venstre) + trykk NEP-logo (høyre) → tilbakestiller alle. |
| Internett ikke tilgjengelig | Sjekk Slate 7 Router og WAN-kabel (kabel 030). |
| Pi viser «via Tailscale» | Normalt ved bortfall av LAN. Failover er aktiv. Sjekk LAN-kabel til Pi. |
| Satellite frakoblet (oransje) | Watchdog forsøker automatisk restart. Vent 30 sek. Hvis vedvarer: restart Pi. |

### Feilsøking Satelitt Pi-er (detaljert)

**Stream Deck viser «Connected» men Companion-knapper virker ikke:**

Watchdog skal håndtere dette automatisk. Hvis det ikke løser seg:

```bash
# SSH inn på aktuell Pi, kjør:
sudo systemctl restart satellite
```

Hvis det ikke hjelper:
```bash
conntrack -D -p tcp -d 192.168.8.101 --dport 16622 2>/dev/null || true
conntrack -D -p tcp -d 192.168.8.101 --dport 8000 2>/dev/null || true
ip route flush cache 2>/dev/null || true
sudo systemctl restart satellite
```

**Pi er koblet på LAN men trafikken går via VPN:**

```bash
journalctl -t nep-ts-failover -f
```

Hvis loggen viser «LAN OK» men ruting fortsatt er feil:
```bash
sudo ip rule add to 192.168.8.0/24 lookup main priority 50
sudo ip route flush cache
```

**Pi er koblet til via internett men fungerer ikke:**
1. Restart Pi
2. Sjekk at Tailscale er tilkoblet: `tailscale status`
3. Hvis ikke tilkoblet: `sudo tailscale up`
4. Hvis vedvarer: kontakt Joakim

**Hente full diagnose fra Pi (til feilsøking på avstand):**
- Fra dashbordet: trykk **🔍 Diagnose** på Pi-kortet → fil lastes ned automatisk
- Via SSH: `curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/scripts/nep-diagnose.sh | bash`

---

## 12. KONTAKT OG RESSURSER

| | |
|---|---|
| Teknisk support Kommentatorkit | Joakim Blyverket — tlf: 984 90 528 |
| Bitfocus Companion | https://bitfocus.io/companion |
| BMD Videohub support | https://www.blackmagicdesign.com/support |
| NEP GitHub (scripts/installer) | https://github.com/medic02/NEP-CommentaryPi |
| Satellite Dashboard | http://192.168.8.101:8080 |
| Companion UI | http://192.168.8.101:8000 |
