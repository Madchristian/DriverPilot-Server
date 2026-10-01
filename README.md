# DriverPilot-Server: betreute Ferndiagnose (Pilot)

Serverseite zu [DriverPilot](https://github.com/Madchristian/DriverPilot) „Hilfe von Christian“.
Fachliche Übergabe und Abnahme: [DriverPilot Issue #19](https://github.com/Madchristian/DriverPilot/issues/19).
Aktueller Stand und offene Punkte: [STATUS.md](STATUS.md). Bedienung und Betrieb: [docs/HANDBUCH.md](docs/HANDBUCH.md).

Der Server nimmt Diagnoseberichte nach dem Vertrag `contract/v1` (byte-exakte Kopie aus dem
DriverPilot-Repo, Quell-Commit in `contract/CONTRACT_SOURCE`) entgegen, hält sie 7 Tage, und
Christian gibt in einer Adminansicht ein Ergebnis frei, das der Client abholt. Optional erzeugt
ein Modelladapter vorher einen Entwurf; im Pilot ist kein echter Anbieter angebunden.

## Aufbau

```
driverpilot_server/
  config.py     Einstellungen aus DP_*-Umgebungsvariablen; Limits nur verschärfbar
  contract.py   lädt Schemas/rules.json/errors.json aus contract/v1; Prüfreihenfolge der Annahme
  db.py         SQLite (WAL, secure_delete), Schema
  service.py    Fachlogik: Pairing, Fälle, Idempotenz, Zustandsautomat, Freigabe, Worker-Leases, Bereinigung
  api.py        Client-API /api/v1 (Starlette), Fehlerobjekte, Rate-Limits, Bodygrenze
  admin.py      Adminansicht (eigener Port), Authentik-Header nur vom Proxy, CSRF
  worker.py     Hintergrundworker + Adapter (none | test)
  main.py       startet API, Admin, Worker, Bereinigung in einem Prozess
contract/       Vertrag v1 (Schemas, Fixtures, Regeln) + validate_contract.py
tests/          pytest gegen alle Vertrags-Fixtures, Transportfälle, Isolation, Worker, Admin
deploy/         Traefik-/DNS-Schnipsel für TrueNAS, Pi-Traefik, Cloudflare
```

Ein Prozess, zwei Ports:

| Port | Zweck | Erreichbar über |
|---|---|---|
| 8140 | Client-API `/api/v1`, `/healthz`, `/readyz` | Cloudflare → UDM → TrueNAS-Traefik (`cloudflare-only`) → `10.0.30.3:8140` |
| 8141 | Adminansicht | Pi-Traefik `dns-prod-2` (`agent-secured` + Authentik `sso`) → `10.0.30.3:8141` |

Der Admin-Port nimmt Identitätsheader (`X-authentik-username`, `X-authentik-groups`) nur von
`DP_ADMIN_TRUSTED_PROXIES` an und verlangt die Gruppe `DP_ADMIN_GROUP`. Jede Mutation braucht
einen CSRF-Token (HMAC-signiertes Cookie + Formularfeld) und einen same-origin Fetch-Kontext.

## Entwicklung

```
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python contract/validate_contract.py contract/v1   # Vertrag selbst konsistent?
.venv/bin/python -m pytest -q                                # Server gegen den Vertrag
DP_ADMIN_DEV_USER=dev DP_DATA_DIR=./data .venv/bin/python -m driverpilot_server.main
```

Mit `DP_ADMIN_DEV_USER` (und ohne `DP_ADMIN_TRUSTED_PROXIES`) ist die Adminansicht lokal ohne
Proxy nutzbar; im Betrieb bleibt die Variable leer.

## Vertragsumsetzung

- `POST /cases` prüft in der Reihenfolge aus `contract/v1/README.md` (Schritte 1–14). Der
  Idempotency-Key gilt je Client und Endpunkt, wird erst mit 202/201 gebunden; gleicher Key +
  gleiche Bytes liefert den Fall im aktuellen Zustand, andere Bytes 409, nach Löschung 409
  `request_retired` (inhaltsfreier Tombstone bis zum Ablauf des Zugangs).
- `report_sha256` = SHA-256 über die exakt empfangenen Body-Bytes.
- Zustände/Übergänge aus `states.json` werden erzwungen (`Contract.transition_allowed`).
  Kein Clientzugriff sieht je einen Entwurf; `result` nur bei `released`.
- `poll_after_seconds`: 10 (`queued`, `analyzing`), 30 (`awaiting_review`), `null` sonst.
- ETag = HMAC über Fallzustand (stark, opak); `If-None-Match` → 304 ohne Body.
- Textmarker aus `rules.json` werden mit demselben Regex-Dialekt angewandt; Treffer → ganzer
  Upload 422 `text_rejected`, ohne Angabe von Feld oder Fundstelle.
- Limits (rules.json) sind Defaults; `.env` darf sie nur verschärfen.
- Einladungen sind per Default einmalig (24 h). Serverintern können sie mit begrenzter
  Mehrfachnutzung angelegt werden (Weitergabe an mehrere Freunde); für den Client ist das
  unsichtbar, jede Einlösung erzeugt einen eigenen Zugang (30 Tage, Token nur gehasht).

## Betrieb auf rpi4-400

```
git clone <repo> ~/driverpilot-server && cd ~/driverpilot-server
cp .env.example .env            # ggf. anpassen
mkdir -p data && sudo chown 10001:10001 data && chmod 700 data
docker compose up -d --build
curl -s http://127.0.0.1:8140/readyz     # ready
curl -s http://127.0.0.1:8140/api/v1/capabilities | head -c 200
```

Update: `git pull && docker compose up -d --build`. Rollback: vorherigen Commit auschecken und
dasselbe Kommando; das Datenbankschema wird nur ergänzt, nie umgebaut (`CREATE TABLE IF NOT EXISTS`).

Neustart verliert keine angenommenen Fälle (SQLite, `synchronous=FULL`). Leases, die beim
Neustart offen waren, werden beim Start als `analysis_failed`/`outcome_unknown` markiert und in
der Adminansicht sichtbar. Bereinigung läuft stündlich: abgelaufene Fälle werden physisch
gelöscht (secure_delete + WAL-Checkpoint), Audit nach 30 Tagen, Tombstones mit Ablauf des Zugangs.

### Datenschutz und Backups

`./data` enthält Diagnoseberichte. Es wird **nicht** in die Pi-Backups aufgenommen (Pilotstandard
aus Issue #19 §9). Gesichert werden nur Repo, `.env` und Deployment. Storageverlust kann
Pilotfälle verlieren; der Nutzer kann neu senden. Logs enthalten keine Bodies, Tokens oder
Einladungen; das Audit nur Metadaten (Akteur, Operation, Fall-ID, Ergebnis).

### Datenschutzhinweis

`privacy_notice.txt` ist der Text, den der Client vor der Zustimmung anzeigt. Jede Änderung
braucht eine neue `DP_PRIVACY_NOTICE_VERSION`; Berichte mit alter Version werden mit
`privacy_notice_outdated` abgelehnt und der Client holt eine neue Zustimmung ein.

### Modelladapter

`DP_AI_PROVIDER=none`: keine Aufträge, alle Fälle `awaiting_review`, `/capabilities` meldet
`external_ai_offered=false`, der Client bietet die KI-Option nicht an.
`test`: synthetischer Adapter, jeder Text trägt `TESTADAPTER`; nur für Tests.
`codex` (Pilot-Entscheidung Christian, 2026-10-01): ChatGPT über denselben OAuth-Weg wie die
Codex-CLI (Device-Code-Login in der Adminansicht unter „KI (ChatGPT)“ oder Import einer
`~/.codex/auth.json`). Tokens liegen in `/data/codex-auth.json` (0600) und werden per
Refresh-Token erneuert. **Ohne Login** meldet `/capabilities` `external_ai_offered=false` und
alle Fälle laufen manuell; Fälle mit KI-Zustimmung warten in `queued`, bis ein Login da ist.
Der Worker sendet den Bericht als reine Daten mit festen Anweisungen (`driverpilot_server/codex.py`,
`INSTRUCTIONS`, Promptversion in `drafts.prompt_version`) an `/responses` mit `store=false` und
prüft die Antwort gegen Schema und Belegregeln; unbrauchbare Antworten → `output_rejected`.
Schnittstelle für weitere Anbieter: `Adapter.analyze(report) -> AdapterResult`, `available()`.
Pilotdefaults: ein gleichzeitiger Aufruf, höchstens zwei Versuche je Fall, 90 s Timeout,
Timeout = `outcome_unknown` ohne Neuversuch, Tagesbudget (`DP_AI_DAILY_CALLS`) atomar reserviert.
Der Datenschutzhinweis nennt OpenAI als Empfänger (Version `2026-10-01.2`).
