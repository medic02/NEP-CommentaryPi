# Testbildegenerator (Companion Pi)

En Flask-app på Companion Pi som genererer testbilde til BMD Videohub-kjeden
via en HDMI→SDI-converter: fargestolper (SMPTE/Full/Ramp/egendefinert),
sprett-logo-skjermsparer, og en samling NEP-brandede skjermsparere.
Vises fullskjerm som en Chromium-kiosk, styres fra en egen admin-side slik
at ingen betjening av viewen risikerer å forstyrre selve visningen.

## Arkitektur

- **`server.py`** — Flask-backend. Holder all tilstand i ett `STATE`-dict,
  persistert til `state.json` og kringkastet live til alle tilkoblede
  klienter via Server-Sent Events (`/api/stream`). Bytter faktisk
  skjermmodus (interlace/progressiv, Hz) via `xrandr` når formatet endres —
  ikke bare canvas-størrelsen.
- **`templates/admin.html`** — Kontrollpanelet (`/`). Alt du styrer fra:
  modus, format, tekst, logoer, klokke/nedtelling, egendefinert
  fargestolpe-editor med live forhåndsvisning, lagrede design ("Mine
  design"), og et bibliotek for skjermsparer-logoer.
- **`templates/display.html`** — Selve visningen (`/display`), det eneste
  som vises på kiosken. Rendrer fargestolper/sprett-logo på canvas, eller
  viser en skjermsparer i en iframe.
- **`screensavers/`** — Statisk HTML/JS/CSS for 7 skjermsparere (DVD,
  Matrix, Pong, Pulse, Starfield, Time, Toasters), hostet lokalt siden
  originalkilden sitter på et internt OB-produksjonsnett som ikke er nåbart
  fra Companion Pi.

## API for Stream Deck / Companion-knapper

`/api/deck` gir en selvdokumenterende oversikt (GET, ingen JSON-body
nødvendig — limes rett inn i en Companion "http: GET"-knapp):

| Endepunkt | Gjør |
|---|---|
| `/api/deck/set?key=<felt>&value=<verdi>` | Setter et hvilket som helst felt (mode, format, barsPattern, screensaver, ...) |
| `/api/deck/toggle?key=<felt>` | Vipper en av/på-bryter (textOn, clockOn, countdownOn) |
| `/api/deck/preset?name=<navn>` | Laster et lagret design |
| `/api/deck/screensaver-logo?name=<filnavn\|default>` | Bytter/tilbakestiller skjermsparer-logo |
| `/api/deck/state` | Full status som JSON (til Companion-variabler/feedback) |

## Installasjon

Del av `install-companion.sh` i repo-roten — kjør den, ikke dette manuelt,
med mindre du feilsøker ett enkelt steg:

```bash
curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install-companion.sh | bash
```

Det scriptet:
1. Kopierer `server.py` + `templates/` + `screensavers/` til `/home/pi/testbilde-server/`
2. Lager en Python venv og installerer Flask
3. Setter opp `nep-testbilde.service` (lytter på port 5050)
4. Setter opp kiosk-oppstart: `.xinitrc` (matchbox-window-manager + Chromium
   `--kiosk`), autologin på tty1, `startx` fra `.bash_profile`

## Kjente fallgruver

- **Kiosken laster ikke ny kode selv.** Chromium-vinduet kjører
  kontinuerlig og laster `display.html`/admin.html sin JavaScript kun én
  gang når siden åpnes. Server-side endringer (nye funksjoner, bugfikser)
  krever at kiosk-vinduet faktisk laster siden på nytt — det skjer ikke av
  seg selv. Trigger det med `xdotool key F5` mot X-displayet, eller en
  reboot.
- **Bilde-URL-er caches av nettleseren.** Hvis noe skal kunne bytte ut et
  bilde bak en URL som allerede er lastet (f.eks. skjermsparer-logoen),
  må enten URL-en selv endre seg (slik skjermsparer-logo-biblioteket gjør —
  hver opplastet logo får sitt eget filnavn) eller svaret ha eksplisitte
  `Cache-Control: no-cache`-headere.
- **Telemetri-tellere må nullstilles ved modusbytte.** Sprett-logo-modusens
  frame-timing-telemetri (`telemetryLastT` i `display.html`) samler et
  tidsstempel kun mens modusen faktisk kjører. Hvis den ikke nullstilles
  når modusen gjenopptas etter en pause, regner den ut differansen mot et
  steinalder-tidsstempel og rapporterer et falskt kjempelangt "bilde" —
  dette var årsaken til flere tilsynelatende katastrofale "frys" i loggen
  som aldri var reelle.
- **`accept-routes` på selve Companion Pi må stå til `false`**, ikke
  `true`, selv om Satellite-Pi-ene (og ruteren) skal ha den på `true`.
  Companion Pi er allerede direkte på LAN-subnettet (`192.168.8.0/24`) —
  skrur man på route-aksept der også, lærer den en konkurrerende rute til
  sitt eget subnett via Tailscale, som ødelegger TCP-tilkoblinger fra
  andre enheter på LAN-et (ping funker fortsatt, men porter som 8000/16622
  slutter å svare). Dette rammet riggen live 2026-10-06.
