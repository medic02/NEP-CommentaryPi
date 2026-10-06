# NEP Kommentatorkit

Automatisk installasjon av hele kittet: Satellite Pi-er (failover, health
API, NEP-logo) og Companion Pi (health API, RAM-database, testbildegenerator
med kiosk-visning). Bygg et nytt kit ved å kjøre riktig installer på hver Pi.

## Struktur

```
nep-kommentatorkit/
├── install.sh                        # Satellite Pi-installer
├── install-companion.sh              # Companion Pi-installer
├── install-health.sh                 # Health API alene (delt av begge over)
├── scripts/
│   ├── nep-ts-failover.sh            # Failover script (LAN → Tailscale)
│   └── cards.js                      # Companion Satellite splash screen
├── services/
│   ├── nep-health.service
│   ├── nep-iprule.service
│   ├── nep-ts-failover.service
│   └── nep-ts-failover.timer
├── health/
│   └── health.py                     # Health API (port 8080)
├── companion/
│   └── ...                           # RAM-database for Companion Pi (se companion/README.md)
├── testbilde/
│   └── ...                           # Testbildegenerator + kiosk for Companion Pi (se testbilde/README.md)
└── assets/
    └── nep-logo.png                  # NEP-logo for Stream Deck splash
```

## Installasjon på ny Satellite Pi

> Forutsetter at Companion Satellite allerede er installert.

```bash
curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install.sh | bash
```

Følg instruksjonene – du velger Pi-nummer og logger inn på Tailscale.

## Installasjon på ny Companion Pi

> Forutsetter at Bitfocus Companion allerede er installert og kjører
> (`systemctl status companion`), og at HDMI→SDI-converteren er tilkoblet
> hvis du vil bruke testbildegeneratoren.

```bash
curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install-companion.sh | bash
```

Se [`testbilde/README.md`](testbilde/README.md) for detaljer om hva
testbildegeneratoren gjør, og [`companion/README.md`](companion/README.md)
for RAM-databasen.

## Hva scriptet gjør

1. Installerer pakker (python3, curl, iproute2, conntrack)
2. Setter opp Health API på port 8080
3. Installerer forbedret failover-script
4. Setter opp alle systemd services og timer
5. Installerer Tailscale (hvis ikke allerede installert)
6. Erstatter icon.png og cards.js med NEP-versjon
7. Restarter satellite-servicen

## Failover-logikk

- Sjekker LAN hvert **5. sekund**
- Fallerer over til Tailscale etter **4 påfølgende feil** (~20 sek)
- Returnerer til LAN etter **3 påfølgende OK** (~15 sek)
- Bruker `flock` – aldri parallelle kjøringer
- Restarter `satellite.service` ved rutebytte for ren reconnect
- Nullstiller tellere ved nettverksendring + 15 sek settle-tid

## Oppdatere eksisterende Pi

```bash
curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install.sh | bash
```

Scriptet er idempotent – trygt å kjøre på nytt.

## Nyttige kommandoer

```bash
# Se failover-status live
journalctl -t nep-ts-failover -f

# Se health API
curl http://localhost:8080/health | python3 -m json.tool

# Sjekk alle NEP-services
systemctl status nep-health nep-iprule nep-ts-failover.timer
```

## Assets

Legg `nep-logo.png` i `assets/`-mappen i repoet.
Scriptet kopierer den til `/opt/companion-satellite/satellite/assets/icon.png`.

## Companion Pi — RAM-database

`install-companion.sh` setter dette opp automatisk hvis USB-disken
allerede er montert på `/home/companion`. Unngår at periodiske
databasebackuper blokkerer Node.js sin event loop og dropper alle
Satelitt Pi-er samtidig. Se [`companion/README.md`](companion/README.md)
for detaljer — inkludert en kjent regresjon som dukker opp igjen ved hver `companion-update`
med mindre `companion-ramdb.service` restartes etterpå.
