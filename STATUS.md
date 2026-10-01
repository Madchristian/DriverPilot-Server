# Status (für alle, die hier weiterarbeiten)

Übergreifende Source of Truth bleibt [DriverPilot #19](https://github.com/Madchristian/DriverPilot/issues/19).
Diese Datei ist das Logbuch der Serverseite. Bitte bei jeder Etappe fortschreiben.

## Entscheidungen (von Christian bestätigt, 2026-10-01)

| Punkt | Entscheidung |
|---|---|
| Host | `rpi4-400` (10.0.30.3), Docker Compose in `~/driverpilot-server` |
| API-Basis | `https://driverpilot.cstrube.de/api/v1` (Cloudflare proxied → TrueNAS-Traefik → Pi) |
| Admin | `https://driverpilot.dns-prod-2.local.cstrube.de` (nur LAN/Tailnet, Authentik-Gruppe Homelab-Admins) |
| Repo | `Madchristian/DriverPilot-Server` (privat) |
| Vertrag | `contract/v1` = Kopie aus DriverPilot Commit `3c1becd` (siehe `contract/CONTRACT_SOURCE`), unverändert bestätigt |
| KI | `none` (manuell). Kein Anbieter bis Freigabe von Anbieter/Region/Budget |
| Einladungen | Einmal (Default) oder Mehrfach (Admin-Option), damit ein Code an mehrere Freunde gehen kann |

## Etappen

- [x] Vertrag vendoren, Validator grün (`11 schemas, 27 error codes, 22 valid, 38 invalid`)
- [x] Server implementiert (API, Admin, Worker, Bereinigung), 80 Tests grün
- [x] Repo auf GitHub: https://github.com/Madchristian/DriverPilot-Server (Deploy-Key read-only fuer rpi4-400)
- [x] Deployment auf rpi4-400 (`~/driverpilot-server`, Compose, healthy), Smoke-Test im LAN: readyz/capabilities/404-Fehlerobjekt/Admin-403 ohne Proxy
- [x] Pi-Traefik: Admin-Router live (`driverpilot.dns-prod-2.local.cstrube.de` → 302 Authentik); Identitaetsheader nur von dns-prod-2 (10.0.30.5/10.0.20.162)
- [ ] TrueNAS-Traefik: `deploy/truenas-traefik-driverpilot.yml` + Cloudflare-Record (`deploy/cloudflare-records.tf.snippet`) — **braucht Christians Go** (öffentliche Exposition)
- [ ] Realer HTTPS-Test von außerhalb (Zertifikatskette, Redirect-Verhalten, Fehlerobjekte)
- [ ] Datenschutzhinweis-Text mit Christian final abstimmen (dann Version anheben)
- [ ] Windows-E2E mit dem DriverPilot-Client (DriverPilot-Agent); Einladungscode über sicheren Kanal
- [ ] Drei READY-Reviews (Security/Privacy, API/State, Betrieb/UX) desselben Stands
- [ ] Erster betreuter realer Fall

## Was der DriverPilot-Agent wissen muss

- `GET /capabilities` liefert `protocol_version 1.0`, `report_schema_versions ["1.0"]`,
  `privacy_notice.version` aktuell `2026-10-01.1` (Text in `privacy_notice.txt`),
  `external_ai_offered=false` solange `DP_AI_PROVIDER=none`.
- Alle Fehlerantworten sind Fehlerobjekte nach `error.schema.json` mit festen deutschen Texten
  (`driverpilot_server/contract.py`, `ERROR_MESSAGES`). Hinter Cloudflare/CrowdSec können im
  Blockfall Plain-403/429 ohne JSON kommen; Statuscode-Fallback aus CLIENT.md bleibt nötig.
- `poll_after_seconds`: queued/analyzing 10, awaiting_review 30, released/analysis_failed null.
- Ein Clientzugang: 30 Tage, 30 Requests/Minute, 5 neue Fälle/Tag.
- Pairing-Fehlversuche: 5 je IP je 15 Minuten → 429 mit `Retry-After`.
- Für den E2E-Test erzeugt Christian in der Adminansicht eine Einladung; Code + Basis-URL
  kommen über einen sicheren Kanal, nie über ein Issue.

## Betriebsnotizen

- dns-prod-2 routet Pakete zur .3 ueber `eth0.20` (`ip route get 10.0.30.3` → src 10.0.20.162), obwohl
  eth0 10.0.30.5/24 traegt. Deshalb stehen beide Adressen in `DP_ADMIN_TRUSTED_PROXIES`. Wird das
  Routing der Pi einmal korrigiert, bleibt die Liste gueltig.
- Backup der Pi-Traefik-Config vor der Aenderung: `~/traefik/data/config.yml.bak-driverpilot-<datum>`.

## Bekannte Grenzen / bewusst nicht gemacht

- Rate-Limits und Pairing-Fehlerzähler leben im Prozessspeicher (kein IP-Logging; Neustart
  setzt sie zurück).
- Ein Prozess, SQLite serialisiert über ein Lock; für den Pilot (wenige Clients) ausreichend,
  gemessen wird nach dem Deployment.
- Admin-Editor ist ein JSON-Textfeld mit serverseitiger Schema-/Belegprüfung und Vorschau der
  freigegebenen Revisionen; kein Formular je Feld.
- Keine Datenträgerverschlüsselung auf der Pi-SSD (Plattform bietet das nicht sicher an);
  dokumentiert, nicht behauptet.
