# Handbuch: DriverPilot-Ferndiagnose („Hilfe von Christian“)

Stand 2026-10-01 (SvelteKit-Oberfläche). Gilt für den Server in diesem Repo (Pilot auf `rpi4-400`) und die Funktion
„Hilfe von Christian“ in DriverPilot ab dem Stand nach 0.3.4.

Inhalt:

1. [Was das Ganze macht](#1-was-das-ganze-macht)
2. [Für Freunde: Hilfe anfordern](#2-für-freunde-hilfe-anfordern)
3. [Für Christian: Fälle bearbeiten](#3-für-christian-fälle-bearbeiten)
4. [KI-Entwürfe über ChatGPT](#4-ki-entwürfe-über-chatgpt)
5. [Betrieb](#5-betrieb)
6. [Störungen und Fehlercodes](#6-störungen-und-fehlercodes)

## 1. Was das Ganze macht

Ein Freund mit einem PC-Problem schickt aus DriverPilot einen bereinigten Diagnosebericht an
Christians Server. Christian liest den Bericht in einer Admin-Ansicht, schreibt eine Antwort mit
Fakten, Vermutungen und konkreten manuellen Schritten (oder lässt sich von ChatGPT einen
Entwurf vorschreiben) und gibt sie frei. DriverPilot zeigt dem Freund nur freigegebene Antworten
und führt nichts davon selbst aus.

```
Freund (DriverPilot)  --HTTPS-->  driverpilot.cstrube.de  -->  Server auf rpi4-400
Christian (Browser)   --LAN/Tailnet + Authentik-->  Admin-Ansicht auf demselben Server
Server                --optional-->  ChatGPT (Entwurf, nur mit Zustimmung des Freundes)
```

Der Server ist kein Fernzugriff und keine Remote-Shell. Er installiert keine Treiber und läuft
nicht als Dauerdienst auf dem PC des Freundes. Der Bericht enthält keine Gerätenamen,
Seriennummern, Pfade, Ereignistexte oder IP-Adressen. Erkennt der Server so etwas, lehnt er den
Bericht ab.

Ein Fall lebt 7 Tage ab Eingang und wird dann automatisch gelöscht. Der Freund kann ihn
jederzeit vorher aus DriverPilot löschen.

## 2. Für Freunde: Hilfe anfordern

### 2.1 Was du brauchst

DriverPilot in einer Version, die den Bereich „Hilfe von Christian“ enthält. Von Christian
bekommst du die Serveradresse `https://driverpilot.cstrube.de` und einen Einladungscode
(32 Zeichen), beides per Nachricht. Ein ChatGPT-Konto brauchst du nicht.

### 2.2 Koppeln (einmalig)

1. In DriverPilot „Hilfe von Christian“ öffnen und auf „Koppeln“ gehen.
2. Serveradresse und Einladungscode eintragen und bestätigen.
3. DriverPilot bekommt einen Zugang, der 30 Tage gilt. Der Code ist danach verbraucht. Bei
   einem Mehrfachcode ist eine Einlösung weniger übrig.

Ist der Zugang abgelaufen oder hat Christian ihn widerrufen, meldet DriverPilot „Zugang
ungültig“. Dann holst du dir einen neuen Code bei Christian.

### 2.3 Bericht senden

1. Einen frischen Scan machen. Er darf höchstens 15 Minuten alt sein, sonst lehnt der Server ab.
2. Das Problem beschreiben: Kategorie wählen (WoW-Absturz, PC friert ein, Grafikreset,
   Leistung, Netzwerk, Addon-Fehler, Sonstiges), dazu eine Beschreibung. Schritte zum
   Nachstellen und WoW-Angaben (Spielversion, nur in WoW oder auch anderswo, Addon-Test
   gemacht) sind freiwillig. E-Mail-Adressen, Links, Dateipfade, Passwörter oder Seriennummern
   gehören nicht in den Text, sonst wird der Bericht abgelehnt.
3. Die Vorschau vollständig lesen. Genau das wird gesendet, sonst nichts.
4. Den Datenschutzhinweis lesen. Wenn du das Kästchen „externe KI erlauben“ setzt, darf
   Christian den Bericht zusätzlich von ChatGPT (OpenAI) vorbewerten lassen. Ohne Haken bleibt
   der Bericht auf Christians Server.
5. „Zustimmen und senden“. Der Fall erscheint als „in Bearbeitung“.

Fehlermeldungen erklärt Abschnitt 6.

### 2.4 Antwort lesen

Solange der Bereich geöffnet ist, fragt DriverPilot den Server regelmäßig ab. Sobald Christian
freigegeben hat, siehst du die Antwort. Sie besteht aus einer Zusammenfassung, aus Fakten, die
durch Einträge deines Berichts belegt sind, aus Vermutungen, die ausdrücklich unbewiesen sind,
und aus nächsten Schritten. Jeder Schritt hat eine Begründung, eine Anleitung, eine
Risikoklasse (nur lesen, rückgängig machbar, nur für Experten), die benötigten Rechte, das
erwartete Ergebnis und, wo möglich, einen Rückweg. Du führst die Schritte selbst aus.
Dazu können Rückfragen, Hinweise und Quellenlinks kommen; Links öffnen sich nur auf Klick.

Hast du inzwischen einen neueren Scan gemacht, markiert DriverPilot die Antwort als zu einem
älteren Scan gehörig. Für ein neues Problem oder einen Nachher-Vergleich schickst du einen
neuen Bericht; das wird ein neuer Fall.

### 2.5 Rückmeldung und Löschen

Zu einer Antwort kannst du eine Rückmeldung geben (besser, unverändert, schlechter, nicht
probiert) und eine Notiz dazu schreiben. Höchstens zehn je Fall. Eine Rückmeldung löst keine
neue KI-Anfrage aus.

„Fall löschen“ entfernt Bericht, Entwürfe, Antworten und Rückmeldungen sofort vom Server. Was
mit deinem Haken bereits an ChatGPT übermittelt wurde, holt das Löschen nicht zurück.

## 3. Für Christian: Fälle bearbeiten

### 3.1 Zugang

Die Admin-Oberfläche liegt unter https://driverpilot.dns-prod-2.local.cstrube.de. Sie ist nur aus
dem LAN oder dem Tailnet erreichbar, die Anmeldung läuft über Authentik (Gruppe
`Homelab-Admins`). Aus dem Internet ist sie nicht erreichbar: der öffentliche Weg über die TrueNAS
endet für `/admin` mit „Zugriff verweigert“.

Die Seitenleiste hat die Seiten Fälle, Einladungen, Zugänge, KI (ChatGPT), Releases und Audit.
Unten steht, wer angemeldet ist. Auf dem Handy klappt das Menü über den Knopf links oben auf.

### 3.2 Einladung erzeugen und weitergeben

Auf der Seite Einladungen trägst du optional einen Vornamen für die Begrüßung ein, dazu eine
Bezeichnung für dich, die Gültigkeit in Tagen und die Anzahl der Einlösungen, dann
„Einladungslink erzeugen“. Du bekommst einen Link wie
`https://driverpilot.cstrube.de/einladung#c=…&n=Max` und eine fertige Nachricht zum Kopieren
oder Teilen. Den Link schickst du deinem Freund über einen privaten Kanal (Signal, iMessage,
persönlich), nicht über GitHub-Issues und nicht per E-Mail an Listen. Er erscheint genau einmal.

Die Einladungsseite begrüßt den Freund und führt ihn in drei Schritten durch Download,
Installation und Koppeln; Serveradresse und Code kann er dort mit einem Klick kopieren. Code und
Name stehen im Teil nach `#`, den der Browser nie an einen Server schickt. Nach dem Öffnen
entfernt die Seite ihn aus Adresszeile und Verlauf.

Pro Freund reicht ein Code mit einer Einlösung und 1 bis 7 Tagen Gültigkeit. Für eine Gruppe
passt ein Code mit zum Beispiel 10 Einlösungen und 30 Tagen. Codes, die niemand mehr braucht,
widerrufst du auf derselben Seite.

Jede Einlösung erzeugt einen eigenen Zugang für 30 Tage. Unter Zugänge siehst du alle Zugänge
mit ihrer Fallzahl und kannst einzelne widerrufen. Der Widerruf wirkt beim nächsten Request des
Clients, auch für bestehende Fälle.

### 3.3 Fallübersicht

Die Seite Fälle zeigt Kennzahlen (wartet auf dich, KI läuft oder wartet, fehlgeschlagen, neue
Fälle heute, aktive Zugänge, KI-Aufrufe) und darunter die offenen oder alle nicht abgelaufenen
Fälle mit ihrem Zustand. Sie aktualisiert sich alle 15 Sekunden von selbst.

| Zustand | Bedeutung | Was du tust |
|---|---|---|
| `queued` | wartet auf den KI-Worker (nur mit KI-Haken und aktivem Login) | nichts, oder „Manuell übernehmen“ |
| `analyzing` | KI-Aufruf läuft (bis 300 s) | warten, Aktionen sind gesperrt |
| `awaiting_review` | wartet auf dich | Entwurf prüfen oder schreiben, dann freigeben |
| `released` | eine Revision ist für den Freund sichtbar | bei Bedarf neue Revision |
| `analysis_failed` | KI-Lauf gescheitert, der Grund steht dabei | „Manuell übernehmen“ oder „KI-Neuversuch“ |

### 3.4 Fallseite

Oben stehen Kategorie, Zustand, Zugang, Eingang, Ablauf und die Zahl der KI-Versuche. Läuft
gerade ein KI-Aufruf, zeigt die Seite das an und aktualisiert sich alle 5 Sekunden. Darunter
folgt der Bericht in lesbarer Form: Symptom und
Freitext, Hardware, Geräte (Modellkennung mit Bus, Vendor und Product, Treiberversion,
Problemcode), Befunde (Quelle, Ereignis-ID, Anzahl, Zeitraum, Stufe, Gerät) und der
Erfassungsstatus. Alles außer `complete` im Erfassungsstatus ist eine Lücke, kein unauffälliger
Befund. Auf breiten Bildschirmen steht der Entwurf rechts daneben.

Die Aktionen oben auf der Seite:

- „Manuell übernehmen“ geht aus `queued` oder `analysis_failed`. Ein offener KI-Auftrag wird
  entwertet, der Fall steht danach auf `awaiting_review`.
- „KI-Neuversuch (budgetiert)“ gibt es nur, wenn der Freund externe KI erlaubt hat und der
  Adapter angemeldet ist. Der Versuch zählt gegen das Tagesbudget.
- „Fall löschen“ entfernt alles, genau wie das Löschen durch den Freund.

### 3.5 Entwurf schreiben oder prüfen

Der Bereich Entwurf zeigt entweder den KI-Entwurf (violett markiert: ungeprüft), deinen zuletzt
gespeicherten Entwurf, nach einer Freigabe die letzte Revision als Ausgangspunkt oder eine leere
Vorlage. Der Editor hat drei Ansichten:

- **Formular:** Zusammenfassung, Fakten mit Belegen (Befund, Gerät oder Berichtsfeld aus
  Auswahllisten), Vermutungen mit Bezug auf Fakten, nächste Schritte mit Risiko und Rechten,
  Rückfragen, Hinweise und Quellen. Einträge fügst du mit „+“ hinzu und mit dem Papierkorb
  entfernst du sie.
- **JSON:** derselbe Entwurf als Text, für schnelles Kopieren oder größere Umbauten.
- **Vorschau:** so, wie der Freund das Ergebnis in DriverPilot sieht.

„Prüfen“ validiert ohne zu speichern. „Entwurf speichern“ prüft und speichert. Als JSON sieht
ein Entwurf so aus:

```json
{
  "summary": "Kurzfassung in 1 bis 2000 Zeichen.",
  "facts": [
    {"id": "fact-1", "text": "Belegte Aussage.",
     "references": [{"kind": "finding", "id": "f-001"},
                    {"kind": "device", "id": "dev-01"},
                    {"kind": "report_field", "pointer": "/hardware/bios_version"}]}
  ],
  "hypotheses": [
    {"text": "Vermutung, ausdrücklich unbewiesen.", "proven": false, "fact_refs": ["fact-1"]}
  ],
  "next_steps": [
    {"title": "Kurz", "rationale": "Warum", "instructions": "Manuelle Schritte in Prosa.",
     "risk_class": "read_only", "required_privileges": "none",
     "expected_outcome": "Woran man den Erfolg erkennt.", "rollback": null, "abort_condition": null}
  ],
  "open_questions": ["Rückfrage, wenn Daten fehlen."],
  "warnings": ["Zum Beispiel: kein BIOS-Update ohne Rücksprache."],
  "sources": [{"title": "Offizielle Seite", "url": "https://..."}]
}
```

Beim Speichern prüft der Server diese Regeln:

- Jeder Fakt braucht mindestens einen Beleg: eine `finding`- oder `device`-ID aus diesem
  Bericht oder einen Feldzeiger wie `/hardware/...`, `/symptom/...` oder `/collection/...`.
- Vermutungen haben `proven: false` und verweisen auf Fakt-IDs. Prozentwerte gibt es nicht.
- `risk_class` ist `read_only`, `reversible_change` oder `expert_only`. `required_privileges`
  ist `none`, `standard_user` oder `administrator`.
- Nur Text. Kein Markdown, kein HTML, keine Skripte oder Befehle. Quellen nur mit `https://`,
  ohne Port und Benutzerangabe, und nur offizielle Seiten der Hersteller, von Microsoft oder
  Blizzard.
- Längen: summary 2000 Zeichen, Texte 1000, Anleitung 4000, Titel 200. Das Gesamtergebnis
  darf 64 KiB nicht überschreiten.

Verstöße erscheinen rot unter dem Editor. Einträge mit dem Zusatz „(Hinweis, keine Sperre)“
sind nur Warnungen, etwa bei Textmarkern. Das Kästchen „beruht auf KI-Entwurf“ steuert die
Herkunftsangabe im Ergebnis (`human` oder `ai_assisted_human_reviewed`). Bei einem bearbeiteten
KI-Entwurf lässt du es angehakt.

### 3.6 Freigeben

Der Knopf „Revision N freigeben“ wird aktiv, sobald ein gültiger Entwurf gespeichert und nicht
mehr verändert ist und der Fall in `awaiting_review` oder `released` steht. Nach der Bestätigung ist die Revision
unveränderlich und für den Freund sichtbar. Sie ist an Fall-ID, Scan-ID und den Hash des
Berichts gebunden; der Client prüft das.

Willst du später etwas ändern, speicherst du einen neuen Entwurf und gibst ihn als Revision N+1
frei. Bis dahin bleibt die alte Revision sichtbar. Wurde der Fall zwischenzeitlich geändert, zum
Beispiel in einem zweiten Browser-Tab, lehnt der Server ab und bittet dich, die Seite neu zu
laden.

Unter „Freigegebene Revisionen“ siehst du jede Revision so, wie der Freund sie bekommt. Die
Rückmeldungen des Freundes stehen darunter mit Bezug auf die jeweilige Revision.

## 4. KI-Entwürfe über ChatGPT

### 4.1 Wie es funktioniert

Der Adapter `codex` spricht das ChatGPT-Backend über denselben OAuth-Weg an wie die Codex-CLI,
mit Christians persönlichem ChatGPT-Konto. In die Warteschlange kommen nur Fälle, bei denen der
Freund externe KI erlaubt hat. Der Worker schickt den Bericht als reine Daten mit festen
Anweisungen an das Modell (`store=false`), prüft die Antwort gegen Schema und Belegregeln und
legt sie als KI-Entwurf ab. An den Freund geht davon nichts ohne Prüfung.

Es läuft höchstens ein Aufruf gleichzeitig, mit höchstens zwei automatischen Versuchen je Fall
und 300 s Timeout je Versuch. Das Tagesbudget steht in `DP_AI_DAILY_CALLS` (Default 10). Ein
Timeout gilt als „Ausgang unbekannt“ und wird nicht automatisch wiederholt, damit nichts
doppelt abgerechnet wird. Du entscheidest dann per „KI-Neuversuch“ oder „Manuell übernehmen“.

Gemessen am 2026-10-01: gpt-5.6-sol braucht für einen vollständigen Bericht etwa 2 bis 3
Minuten und rund 7.000 Tokens.

### 4.2 Seite „KI (ChatGPT)“

Der Status zeigt, ob der Server angemeldet ist, das Konto, den Ablauf des Access-Tokens (er wird
automatisch erneuert), den letzten Fehler, das Modell, ob die KI den Clients angeboten wird und
die Aufrufe des Tages.

„Mit ChatGPT anmelden (Device-Code)“ zeigt einen Code an. Den gibst du auf
`https://auth.openai.com/codex/device` ein und lädst die Seite danach neu. Der Code gilt 15
Minuten. Als Alternative kannst du den Inhalt einer `~/.codex/auth.json` einfügen; so wurde am
2026-10-01 der Token des Homelab-Dashboards übernommen. „Abmelden“ löscht die Tokendatei, und
der Server fällt sofort in den manuellen Modus.

Ohne Login meldet `/capabilities` `external_ai_offered=false`. DriverPilot blendet die
KI-Option dann aus und alle Fälle laufen manuell. Fälle, die vorher mit KI-Haken in `queued`
standen, bleiben dort, bis ein Login da ist oder du sie übernimmst.

### 4.3 Hinweise

Dashboard und Ferndiagnose-Server teilen sich derzeit denselben Refresh-Token. Verliert einer
der beiden die Anmeldung, etwa durch Token-Rotation, kopierst du die Tokendatei neu oder machst
hier einen eigenen Device-Login.

In den ChatGPT-Kontoeinstellungen muss „Das Modell für alle verbessern“ aus sein. Der
Datenschutzhinweis sagt das so zu.

Modell und Reasoning stellst du über `DP_CODEX_MODEL` und `DP_CODEX_REASONING` in `.env` ein.
Danach ist ein Neustart nötig.

## 5. Betrieb

### 5.1 Wo was liegt

| Was | Wo |
|---|---|
| Server | `rpi4-400` (10.0.30.3), Docker Compose in `~/driverpilot-server` mit zwei Containern: `driverpilot-server` (Python) und `driverpilot-web` (SvelteKit); Clone von GitHub mit read-only Deploy-Key |
| Daten | `~/driverpilot-server/data/` mit SQLite `driverpilot.sqlite3`, `server.secret` und `codex-auth.json`; uid 10001, Rechte 0700; nicht in Backups |
| Downloads | `~/driverpilot-server/downloads/` (10001:1000, 775), im Container `/downloads`, öffentlich unter `/downloads/`; gefüllt vom Release-Sync |
| Konfiguration | `~/driverpilot-server/.env`, Vorlage ist `.env.example` |
| Öffentliche API | `https://driverpilot.cstrube.de/api/v1`. Der Weg: Cloudflare (proxied, `records.tf`), dann TrueNAS-Traefik mit `dynamic/driverpilot.yml` (`cloudflare-only`, CrowdSec, Rate-Limit), dann `10.0.30.3:8140` |
| Öffentliche Seiten | `https://driverpilot.cstrube.de/` mit Anleitung, Datenschutzhinweis, Downloads und Einladungsseite; TrueNAS-Traefik leitet `/api/`, `/hooks/`, `/downloads/<datei>` und `/readyz` an `:8140` (Python), alles andere an `:8142` (SvelteKit) |
| Admin | `https://driverpilot.dns-prod-2.local.cstrube.de`. Der Weg: Pi-Traefik mit `~/traefik/data/config.yml` (`agent-secured` und `sso`), dann `10.0.30.3:8142` (SvelteKit), von dort intern an die Admin-API `server:8141` |
| Repo und Logbuch | `github.com/Madchristian/DriverPilot-Server`, dort `STATUS.md`; der Auftrag ist DriverPilot Issue #19 |

### 5.2 Tägliche Handgriffe

```bash
ssh christian@10.0.30.3
cd ~/driverpilot-server
docker compose ps                        # healthy?
docker compose logs --since 1h           # keine Bodies/Tokens im Log
curl -s http://127.0.0.1:8140/readyz     # "ready" = DB schreibbar
curl -s http://127.0.0.1:8142/healthz    # "ok" = Oberfläche läuft
curl -s http://127.0.0.1:8140/api/v1/capabilities | head -c 300
```

Von außen prüfst du mit `curl -s https://driverpilot.cstrube.de/api/v1/capabilities` und im Browser
mit https://driverpilot.cstrube.de/. Direkt am
Origin ohne Cloudflare muss 403 kommen, das ist der Origin-Lock.

### 5.3 Update und Rollback

```bash
cd ~/driverpilot-server
git pull && docker compose up -d --build        # Update
git log --oneline -5
git checkout <alter-commit> && docker compose up -d --build   # Rollback
```

Das Datenbankschema wird nur ergänzt (`CREATE TABLE IF NOT EXISTS`), darum läuft ein älterer
Stand auch mit einer neueren Datenbank. Ein Neustart verliert keine angenommenen Fälle. Laufende
KI-Aufrufe markiert der Server beim Start als `analysis_failed` mit Grund `outcome_unknown`.

### 5.4 Release-Dateien veröffentlichen

Neue Releases kommen von selbst: GitHub ruft beim Veröffentlichen eines Releases im
DriverPilot-Repo den Webhook `POST /hooks/github` auf (signiert mit
`DP_GITHUB_WEBHOOK_SECRET`). Der Server wartet, bis `SHA256SUMS.txt` und alle darin
gelisteten Dateien am Release hängen, lädt sie mit `DP_GITHUB_TOKEN` (fine-grained PAT,
„Contents: Read-only“ auf dem Client-Repo), prüft jede Datei gegen die Prüfsumme und tauscht
erst dann in `/downloads`. Von exe und zip bleiben die `DP_RELEASES_KEEP` neuesten Versionen,
`DriverPilot.cer`, `SHA256SUMS.txt` und `ZERTIFIKAT-ANLEITUNG.txt` werden überschrieben.

Von Hand geht es auf der Admin-Seite Releases („Release jetzt holen“, Tag oder leer für das
neueste) oder per Endpunkt, zum Beispiel aus der CI:

```bash
curl -X POST -H "Authorization: Bearer $DP_RELEASE_SYNC_TOKEN" -H "Content-Type: application/json" \
  --data '{"tag":"v0.4.0"}' https://driverpilot.cstrube.de/hooks/sync-release
```

Die Seite Releases zeigt den letzten Lauf mit Meldung. Als Rückfallweg bleibt
`deploy/publish-release.sh v0.3.4` auf `dns-prod-2`: es lädt die Dateien mit `gh`, prüft sie
und kopiert sie per scp in den Download-Ordner.

### 5.5 Einstellungen in `.env`

| Variable | Bedeutung |
|---|---|
| `DP_API_TRUSTED_PROXIES` | Proxy, dessen `CF-Connecting-IP` für Rate-Limits zählt (`10.0.30.20`) |
| `DP_ADMIN_API_TOKEN` | gemeinsames Token zwischen Oberfläche und interner Admin-API |
| `ADMIN_HOSTS`, `ADMIN_TRUSTED_PROXIES`, `ADMIN_GROUP` | Admin-Oberfläche: Hostname, Proxys mit gültigen Authentik-Headern (`10.0.30.5,10.0.20.162`; die Pi erreicht die .3 über VLAN20), Authentik-Gruppe |
| `DP_PUBLIC_BASE_URL` | Basis der Einladungslinks und Serveradresse für die Clients |
| `DP_PRIVACY_NOTICE_VERSION` und `DP_PRIVACY_NOTICE_FILE` | bei jeder Textänderung die Version anheben; alte Zustimmungen werden abgelehnt und DriverPilot holt eine neue |
| `DP_DOWNLOADS_DIR` | Verzeichnis der Release-Dateien im Container (Default `/downloads`) |
| `DP_CLIENT_REPO`, `DP_GITHUB_TOKEN`, `DP_GITHUB_WEBHOOK_SECRET`, `DP_RELEASE_SYNC_TOKEN`, `DP_RELEASES_KEEP` | Release-Sync: Client-Repo, GitHub-Token (Contents: read), Webhook-Secret, Bearer-Token für den Endpunkt, behaltene Versionen |
| `DP_AI_PROVIDER` | `none`, `test` oder `codex` |
| `DP_CODEX_MODEL`, `DP_CODEX_REASONING` | Modellwahl |
| `DP_AI_DAILY_CALLS`, `DP_AI_TIMEOUT_SECONDS` | Budget und Timeout |
| `DP_MAX_NEW_CASES_PER_CLIENT_PER_DAY` (5), `DP_MAX_NEW_CASES_GLOBAL_PER_DAY` (30), `DP_MAX_OPEN_CASES_GLOBAL` (100), `DP_CLIENT_REQUESTS_PER_MINUTE` (30) | Limits, sie dürfen nur verschärft werden |

Änderungen wirken nach `docker compose up -d`.

### 5.6 Datenschutzhinweis ändern

Zuerst `privacy_notice.txt` im Repo anpassen (Empfänger, Zweck, KI-Anbieter, Löschfrist). Dann
`DP_PRIVACY_NOTICE_VERSION` in `.env` auf einen neuen Wert setzen, zum Beispiel Datum und Zähler.
Zum Schluss committen, pushen und auf der Pi `git pull && docker compose up -d --build`
ausführen.

### 5.7 Bereinigung, Audit, Logs

Stündlich löscht der Server abgelaufene Fälle physisch (SQLite `secure_delete` plus
WAL-Checkpoint), dazu Tombstones nach Ablauf des Zugangs, Audit-Einträge nach 30 Tagen und
verbrauchte Einladungen.

Die Admin-Seite Audit zeigt, wer wann was mit welchem Fall gemacht hat, ohne Berichtinhalt.

Das Container-Log enthält Start und Stop, Worker-Meldungen und Warnungen. Bodies, Tokens,
Einladungen und Modellantworten stehen nie im Log. Codex-Aufrufe erscheinen nur mit Länge und
Tokenverbrauch.

### 5.8 Vertrag aktualisieren

Der Vertrag liegt unter `contract/v1` als byte-exakte Kopie aus dem DriverPilot-Repo;
`contract/CONTRACT_SOURCE` nennt den Commit. Änderungen stimmst du zuerst dort per PR ab. Dann
ersetzt du `v1/`, aktualisierst `CONTRACT_SOURCE` und lässt
`.venv/bin/python contract/validate_contract.py contract/v1` und `pytest` laufen.

## 6. Störungen und Fehlercodes

### 6.1 Was DriverPilot dem Freund meldet

| Code | Bedeutung | Abhilfe |
|---|---|---|
| `invitation_invalid` | Code unbekannt, abgelaufen, verbraucht oder widerrufen | neuen Code von Christian |
| `token_invalid` | Zugang fehlt, nach 30 Tagen abgelaufen oder widerrufen | mit neuem Code neu koppeln |
| `scan_too_old` | Scan älter als 15 Minuten | neuen Scan, erneut senden |
| `clock_skew` | PC-Uhr geht mehr als 5 Minuten vor | Datum und Uhrzeit am PC prüfen |
| `privacy_notice_outdated` | der Hinweis wurde geändert | DriverPilot zeigt den neuen Text, erneut zustimmen |
| `text_rejected` | E-Mail, Link, Pfad, Passwort- oder Seriennummernangabe im Text | Text umformulieren |
| `daily_case_limit_reached` | heute schon 5 Fälle | morgen wieder |
| `capacity_exhausted` oder `service_unavailable` | Server voll oder nicht bereit, nichts gespeichert | später erneut, sonst Christian fragen |
| `rate_limited` | zu viele Anfragen | kurz warten (Retry-After) |
| `not_found` | Fall gelöscht, abgelaufen oder gehört nicht zu diesem Zugang | neuen Bericht senden |
| `schema_violation` oder `unsupported_schema_version` | Client und Server passen nicht zusammen | DriverPilot aktualisieren, sonst Christian |

Alle Codes stehen in `contract/v1/errors.json`.

### 6.2 Typische Serverprobleme

| Symptom | Ursache | Abhilfe |
|---|---|---|
| Admin-Seite meldet „Zugriff verweigert“ trotz Authentik-Login | der Request kommt nicht von einem Proxy in `ADMIN_TRUSTED_PROXIES`, oder die Gruppe fehlt | `.env` prüfen; Routing der Pi mit `ip route get 10.0.30.3` auf dns-prod-2 |
| Admin-Seite meldet „Admin-API lehnt ab (Token prüfen)“ | `DP_ADMIN_API_TOKEN` fehlt oder unterscheidet sich zwischen den Containern | `.env` prüfen, `docker compose up -d` |
| Formular meldet „Cross-site POST form submissions are forbidden“ | Proxy schickt keine `X-Forwarded-Proto`/`X-Forwarded-Host` | Traefik-Router prüfen; lokal `ORIGIN` setzen |
| `external_ai_offered=false` trotz Adapter `codex` | nicht angemeldet oder Token-Refresh gescheitert | Seite „KI (ChatGPT)“: Status und letzter Fehler, neu anmelden |
| Fälle bleiben in `queued` | kein Login, oder der Worker steht | Login prüfen, `docker compose logs`, sonst „Manuell übernehmen“ |
| `analysis_failed` mit `outcome_unknown` | Timeout (300 s) oder Neustart während des Aufrufs | „KI-Neuversuch“ oder manuell |
| `analysis_failed` mit `output_rejected` | die Modellantwort verletzt Schema oder Belege | manuell; das Log zeigt Status und Content-Type, nie den Inhalt |
| `analysis_failed` mit `budget_exhausted` | Tagesbudget erreicht | morgen, oder `DP_AI_DAILY_CALLS` erhöhen |
| `analysis_failed` mit `provider_unavailable` | Netz, 429 oder 5xx bei OpenAI, beide Versuche verbraucht | später „KI-Neuversuch“ |
| `readyz` liefert `not ready` | Datenbank nicht schreibbar (Disk voll, Rechte) | `df -h`, Rechte von `data/` (uid 10001, 0700) |
| von außen 403 | der Request geht nicht über Cloudflare | DNS prüfen: `dig driverpilot.cstrube.de` muss Cloudflare-IPs liefern |
| von außen 522 oder 524 | Traefik auf der TrueNAS erreicht `10.0.30.3:8140` nicht | Container auf der Pi mit `docker compose ps`; Traefik-Datei `dynamic/driverpilot.yml` |

### 6.3 Notfall: alles aus

```bash
cd ~/driverpilot-server && docker compose down     # API und Admin sofort weg, Daten bleiben in data/
```

Die öffentliche Route legst du still, indem du auf der TrueNAS `dynamic/driverpilot.yml`
umbenennst; Traefik lädt das Verzeichnis live. Einladungen und Zugänge widerrufst du jederzeit
in der Admin-Ansicht.
