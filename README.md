# DriverPilot-Server: betreute Ferndiagnose (Pilot)

Serverseite zu [DriverPilot](https://github.com/Madchristian/DriverPilot) „Hilfe von Christian“.
Fachliche Übergabe und Abnahme: [DriverPilot Issue #19](https://github.com/Madchristian/DriverPilot/issues/19).
Aktueller Stand und offene Punkte: [STATUS.md](STATUS.md). Bedienung und Betrieb: [docs/HANDBUCH.md](docs/HANDBUCH.md).

Der Server nimmt Diagnoseberichte nach dem Vertrag `contract/v1` (byte-exakte Kopie aus dem
DriverPilot-Repo, Quell-Commit in `contract/CONTRACT_SOURCE`) entgegen, hält sie 7 Tage, und
Christian gibt in einer Admin-Oberfläche ein Ergebnis frei, das der Client abholt. Optional erzeugt
ein Modelladapter vorher einen Entwurf; im Pilot ist kein echter Anbieter angebunden.

## Aufbau

Zwei Container auf `rpi4-400`:

| Dienst | Port | Aufgabe | Erreichbar über |
|---|---|---|---|
| `server` (Python, Starlette) | 8140 | Client-API `/api/v1` nach Vertrag, Webhooks `/hooks/*`, Release-Dateien `/downloads/<datei>`, `/readyz` | TrueNAS-Traefik, nur diese Pfade |
| `server` | 8141 | interne Admin-JSON-API `/admin-api/*` (Bearer `DP_ADMIN_API_TOKEN` + Akteur) | nur im Compose-Netz |
| `web` (SvelteKit, Svelte 5, Tailwind 4) | 8142 | öffentliche Seiten `/`, `/anleitung`, `/downloads`, `/datenschutz`, `/einladung` und die Admin-Oberfläche `/admin` | TrueNAS-Traefik (öffentlich) bzw. Pi-Traefik mit Authentik (Admin) |

```
driverpilot_server/        Python: Vertrag, Fachlogik, Worker
  config.py  contract.py  db.py  service.py  api.py  admin.py (JSON)  public.py (Downloads)
  worker.py  codex.py  releases.py  ratelimit.py  main.py
web/                       SvelteKit-Oberfläche
  src/routes/(public)/     Start, Anleitung, Downloads, Datenschutz, Einladung
  src/routes/admin/        Fälle, Fallseite mit Entwurfs-Editor, Einladungen, Zugänge, KI, Releases, Audit
  src/lib/server/          Identität (Authentik nur vom Pi-Traefik), Backend-Aufrufe
  src/lib/content/         Anleitung für Freunde (Markdown)
contract/                  Vertrag v1 (Schemas, Fixtures, Regeln) + validate_contract.py
tests/                     pytest gegen alle Vertrags-Fixtures, Transportfälle, Isolation, Worker, Admin-API
deploy/                    Traefik-/DNS-Schnipsel für TrueNAS, Pi-Traefik, Cloudflare
```

Die Admin-Oberfläche verlangt, dass der Request direkt vom Pi-Traefik kommt
(`ADMIN_TRUSTED_PROXIES`) und Authentik einen Benutzer der Gruppe `ADMIN_GROUP` meldet. Erst dann
ruft sie die interne Admin-API mit dem gemeinsamen Token und dem Benutzernamen als Akteur auf.
Formulare sind durch SvelteKits Origin-Prüfung gegen CSRF geschützt; alle Seiten senden eine
strikte CSP mit Nonces.

**Einladungslink:** Die Seite „Einladungen“ erzeugt einen Link
`https://driverpilot.cstrube.de/einladung#c=<code>&n=<Vorname>`. Code und Name stehen im
Fragment, das der Browser nie an einen Server schickt (auch nicht an Cloudflare). Die
Einladungsseite liest es, entfernt es aus Adresszeile und Verlauf und führt durch Download,
Installation und Koppeln mit Kopierknöpfen für Serveradresse und Code. Das weicht bewusst von der
Vertragsregel „Einladungen nie in URLs“ ab, die sich auf HTTP-Anfragen bezieht: Das Fragment
erreicht keinen Server, der Code bleibt einmalig und befristet.

**App-Link:** Die Einladungsseite bietet zusätzlich „In DriverPilot öffnen“ mit
`driverpilot://pair?server=<https-Origin>&code=<Einladungscode>` (Query percent-codiert). Der
Windows-Client muss das Schema `driverpilot` registrieren, `server` auf `https://` ohne Pfad,
Query und Benutzerangabe prüfen, beide Werte nur in die Kopplungsfelder vorbelegen und
`POST /pairings/redeem` erst nach Bestätigung durch den Nutzer senden. Reagiert kein Handler
(Seite bleibt sichtbar), zeigt die Seite den Rückfall mit Kopierfeldern.

## Entwicklung

```
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python contract/validate_contract.py contract/v1   # Vertrag selbst konsistent?
.venv/bin/python -m pytest -q                                # Server gegen den Vertrag
DP_ADMIN_API_TOKEN=dev DP_DATA_DIR=./data .venv/bin/python -m driverpilot_server.main

cd web && npm install && npm run check && npm run build
ORIGIN=http://127.0.0.1:3000 DP_ADMIN_API_TOKEN=dev ADMIN_DEV_USER=dev node build
```

Mit `ADMIN_DEV_USER` (und ohne `ADMIN_TRUSTED_PROXIES`) ist die Admin-Oberfläche lokal ohne
Proxy nutzbar; im Betrieb bleibt die Variable leer. `ORIGIN` braucht es lokal, weil SvelteKit
ohne Proxy-Header sonst `https` annimmt und Formulare als Cross-Site ablehnt.

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
cp .env.example .env            # DP_ADMIN_API_TOKEN setzen, Rest pruefen
mkdir -p data downloads && sudo chown 10001:10001 data && chmod 700 data
sudo chown 10001:$USER downloads && chmod 775 downloads
docker compose up -d --build
curl -s http://127.0.0.1:8140/readyz     # ready
curl -s http://127.0.0.1:8142/healthz    # ok (web)
curl -s http://127.0.0.1:8140/api/v1/capabilities | head -c 200
```

Update: `git pull && docker compose up -d --build`. Rollback: vorherigen Commit auschecken und
dasselbe Kommando; das Datenbankschema wird nur ergänzt, nie umgebaut (`CREATE TABLE IF NOT EXISTS`).

Neustart verliert keine angenommenen Fälle (SQLite, `synchronous=FULL`). Leases, die beim
Neustart offen waren, werden beim Start als `analysis_failed`/`outcome_unknown` markiert und in
der Admin-Oberfläche sichtbar. Bereinigung läuft stündlich: abgelaufene Fälle werden physisch
gelöscht (secure_delete + WAL-Checkpoint), Audit nach 30 Tagen, Tombstones mit Ablauf des Zugangs.

### Datenschutz und Backups

`./data` enthält Diagnoseberichte. Es wird **nicht** in die Pi-Backups aufgenommen (Pilotstandard
aus Issue #19 §9). Gesichert werden nur Repo, `.env` und Deployment. Storageverlust kann
Pilotfälle verlieren; der Nutzer kann neu senden. Logs enthalten keine Bodies, Tokens oder
Einladungen; das Audit nur Metadaten (Akteur, Operation, Fall-ID, Ergebnis).

### Öffentliche Seiten und Downloads

Die Oberfläche (`web`) zeigt eine Anleitung für Freunde (`web/src/lib/content/anleitung.md`), den
Datenschutzhinweis (aus `privacy_notice.txt` über `/public-api/privacy`) und eine Downloadseite
für die signierten Release-Dateien des Windows-Clients. Python liefert die Dateien selbst aus. Die Dateien liegen in `./downloads` und kommen automatisch dorthin: GitHub
ruft beim Veröffentlichen eines Releases `POST /hooks/github` (HMAC-signiert), der Server wartet
auf `SHA256SUMS.txt` plus alle gelisteten Dateien, prüft die Prüfsummen und tauscht atomar ein
(`driverpilot_server/releases.py`). Alternativ `POST /hooks/sync-release` mit Bearer-Token, die
Admin-Seite „Releases“ oder `deploy/publish-release.sh <tag>`. Die Seite zeigt Größe und SHA-256.
Erlaubt sind nur Dateinamen aus `[A-Za-z0-9._-]` mit den Endungen exe, zip, cer, txt, sha256,
pdf, md. Das vollständige Handbuch (`docs/HANDBUCH.md`) bleibt im Repo, weil es interne
Hostnamen enthält.

### Datenschutzhinweis

`privacy_notice.txt` ist der Text, den der Client vor der Zustimmung anzeigt. Jede Änderung
braucht eine neue `DP_PRIVACY_NOTICE_VERSION`; Berichte mit alter Version werden mit
`privacy_notice_outdated` abgelehnt und der Client holt eine neue Zustimmung ein.

### Modelladapter

`DP_AI_PROVIDER=none`: keine Aufträge, alle Fälle `awaiting_review`, `/capabilities` meldet
`external_ai_offered=false`, der Client bietet die KI-Option nicht an.
`test`: synthetischer Adapter, jeder Text trägt `TESTADAPTER`; nur für Tests.
`codex` (Pilot-Entscheidung Christian, 2026-10-01): ChatGPT über denselben OAuth-Weg wie die
Codex-CLI (Device-Code-Login in der Admin-Oberfläche unter „KI (ChatGPT)“ oder Import einer
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

## Lizenz

MIT, siehe [LICENSE](LICENSE). Das gilt auch für die Kopie des Vertrags unter `contract/`.
