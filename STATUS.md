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
| KI | `codex`: ChatGPT über Christians persönliches Konto (Codex-OAuth), Modell `gpt-5.6-sol`, 10 Aufrufe/Tag. **Abweichung von Issue #19 §4** („kein Rückgriff auf Christians ChatGPT-/Codex-OAuth-Login“) – bewusste Entscheidung Christians, weil der Pilot privat bleibt (er und ein Freund). Ohne Login = manueller Modus |
| Einladungen | Einmal (Default) oder Mehrfach (Admin-Option), damit ein Code an mehrere Freunde gehen kann |

## Etappen

- [x] Handbuch für Freunde, Christian und Betrieb: `docs/HANDBUCH.md`

- [x] Vertrag vendoren, Validator grün (`11 schemas, 27 error codes, 22 valid, 38 invalid`)
- [x] Server implementiert (API, Admin, Worker, Bereinigung), 94 Tests grün (inkl. Codex-Adapter gegen nachgebildetes Backend); Dependabot-Meldungen behoben (starlette 1.7, python-multipart 0.0.32, pytest 9.1)
- [x] Repo auf GitHub: https://github.com/Madchristian/DriverPilot-Server (Deploy-Key read-only fuer rpi4-400)
- [x] Deployment auf rpi4-400 (`~/driverpilot-server`, Compose, healthy), Smoke-Test im LAN: readyz/capabilities/404-Fehlerobjekt/Admin-403 ohne Proxy
- [x] Pi-Traefik: Admin-Router live (`driverpilot.dns-prod-2.local.cstrube.de` → 302 Authentik); Identitaetsheader nur von dns-prod-2 (10.0.30.5/10.0.20.162)
- [x] TrueNAS-Traefik `dynamic/driverpilot.yml` + Cloudflare-Record (records.tf, tofu apply) live seit 2026-10-01; Origin-Lock geprüft (Direktzugriff 403)
- [x] HTTPS über die Cloudflare-Edge geprüft: HTTP/2 200 `/capabilities`, Kette Google Trust Services (CF-Edge), `Cache-Control: no-store`, 404/401 als Fehlerobjekte, `WWW-Authenticate: Bearer`; http→https 301 nur an der Edge (Client nutzt ausschließlich https). Test von einem Anschluss außerhalb des Homelabs steht noch aus (Christian/DriverPilot-Agent)
- [x] Codex-Adapter + Adminseite „KI (ChatGPT)“ (Device-Code-Login, auth.json-Import, Logout); Datenschutzhinweis v2026-10-01.2 nennt OpenAI
- [x] ChatGPT-Login: Tokendatei aus dem Homelab-Dashboard übernommen (gleiches Konto; Refresh-Token wird jetzt von zwei Diensten benutzt, bei Rotation ggf. erneut kopieren oder eigenen Device-Login machen)
- [x] Echter Providerlauf mit synthetischem Vertragsbericht am 2026-10-01: Entwurf nach ~2:20 min (7.075 Tokens), schemagültig, in der Adminansicht als KI-ENTWURF; Fall `71125ec3…` wartet auf Prüfung. Gotchas: Backend sendet SSE ohne Content-Type (Erkennung am Inhalt), Timeout 300 s nötig
- [ ] Christian: in den ChatGPT-Kontoeinstellungen Trainingsnutzung prüfen (im Hinweis als abgeschaltet zugesagt)
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
