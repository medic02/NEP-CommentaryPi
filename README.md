# NEP Kommentatorkit – Satellite Pi

Automatisk installasjon av failover, health API og NEP-logo på Satellite Pi-er.

## Struktur

```
nep-kommentatorkit/
├── install.sh                        # Hovedinstaller
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
└── assets/
    └── nep-logo.png                  # NEP-logo for Stream Deck splash
```

## Installasjon på ny Pi

> Forutsetter at Companion Satellite allerede er installert.

```bash
curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install.sh | bash
```

Følg instruksjonene – du velger Pi-nummer og logger inn på Tailscale.

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
