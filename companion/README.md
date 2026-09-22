# Companion Pi — RAM-database

Companion (Bitfocus) lagrer sin database (`db.sqlite`/`cache.sqlite`) i
`/home/companion/.config/companion-nodejs/v<major.minor>/`. På rått
SD-kort/USB-disk blokkerte den periodiske databasebackupen Node.js sin
event loop i 3-6 sekunder, noe som fikk alle Satelitt Pi-er til å droppe
tilkoblingen samtidig (satellite keepalive-pingen timet ut).

Løsningen: mont den versjonerte config-mappen som `tmpfs` (RAM) i stedet,
og synk tilbake til disk periodisk + ved shutdown.

## Filene

| Fil | Formål |
|---|---|
| `companion-ramdb-load.sh` | `ExecStart` for `companion-ramdb.service` — rsync'er config-mappen inn i RAM og bind-monter RAM over original-stien |
| `companion-ramdb-stop.sh` | `ExecStop` for `companion-ramdb.service` — synker og avmonterer ved shutdown/restart av Companion |
| `companion-ramdb-sync.sh` | Kjøres av `companion-ramdb-sync.timer` hvert 5. minutt — rsync'er `db.sqlite`/`cache.sqlite` (+ `.bak`) fra RAM til USB-disken |
| `companion-ramdb.service` | Oneshot, `Before=companion.service`, laster RAM-databasen før Companion starter |
| `companion-ramdb-sync.service` + `.timer` | Periodisk sync til disk |
| `ramdb.conf` | Drop-in på `companion.service` (`/etc/systemd/system/companion.service.d/ramdb.conf`) som gjør Companion avhengig av `companion-ramdb.service` |

## Installasjon (manuell, ikke del av `install.sh`)

Dette er kun for **Companion Pi**, ikke Satelitt Pi-ene — det er en helt
separat mekanisme fra `nep-ts-failover`/`nep-satellite-watchdog`.

```bash
sudo cp companion-ramdb-load.sh companion-ramdb-stop.sh companion-ramdb-sync.sh /usr/local/sbin/
sudo chmod +x /usr/local/sbin/companion-ramdb-*.sh

sudo cp companion-ramdb.service companion-ramdb-sync.service companion-ramdb-sync.timer /etc/systemd/system/
sudo mkdir -p /etc/systemd/system/companion.service.d
sudo cp ramdb.conf /etc/systemd/system/companion.service.d/ramdb.conf

sudo systemctl daemon-reload
sudo systemctl enable --now companion-ramdb.service companion-ramdb-sync.timer
sudo systemctl restart companion
```

## Verifiser

```bash
sudo journalctl -u companion -r --no-pager | grep -m1 'Database backup complete'
# Skal vise noen hundre ms, ikke 2000-6000ms
mount | grep companion-nodejs   # skal vise "type tmpfs"
```

## Kjent regresjon: Companion-oppgradering (2026-09-22)

Companion versjonerer config-mappen sin etter `major.minor`
(`v4.1`, `v4.3`, `v5.0`, ...). Da Companion ble oppgradert fra
`4.3.0` til `5.0.6` via `sudo companion-update`, laget den en helt ny
mappe `v5.0/` — som RAM-mountet (den gang hardkodet til `v4.3`) ikke
dekket. Companion begynte dermed å skrive rett mot USB-disken igjen
uten at noen la merke til det før alle Satelitt Pi-ene droppet ut
samtidig (backup-tid målt til 5780ms, identisk symptom som den
opprinnelige SD-kort-bugen).

**Fiksen:** alle tre scriptene over leser nå Companion-versjonen
dynamisk fra `/opt/companion/BUILD`
(`grep -oE '^[0-9]+\.[0-9]+' /opt/companion/BUILD`) i stedet for å
hardkode `v4.3`. RAM- og USB-helper-stiene følger med (`/run/companion-v50`
osv.), så en fremtidig `companion-update` til f.eks. `5.1` eller `6.0`
plukkes opp automatisk neste gang `companion-ramdb.service` kjører
(dvs. neste `systemctl restart companion` eller reboot).

**Husk etter enhver `companion-update`:** kjør
`sudo systemctl restart companion-ramdb.service && sudo systemctl restart companion`
(eller bare reboot Companion Pi) slik at den nye versjonsmappen faktisk
kommer inn i RAM — companion-update alene restarter kun `companion.service`,
ikke `companion-ramdb.service`.
