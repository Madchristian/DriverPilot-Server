# Handbuch: DriverPilot-Ferndiagnose („Hilfe von Christian“)

Stand 2026-10-01. Gilt für den Server in diesem Repo (Pilot auf `rpi4-400`) und die Funktion
„Hilfe von Christian“ in DriverPilot ab dem Stand nach 0.3.4.

Inhalt:

1. [Was das Ganze macht](#1-was-das-ganze-macht)
2. [Für Freunde: Hilfe anfordern](#2-für-freunde-hilfe-anfordern)
3. [Für Christian: Fälle bearbeiten](#3-für-christian-fälle-bearbeiten)
4. [KI-Entwürfe über ChatGPT](#4-ki-entwürfe-über-chatgpt)
5. [Betrieb](#5-betrieb)
6. [Störungen und Fehlercodes](#6-störungen-und-fehlercodes)

---

## 1. Was das Ganze macht

Ein Freund mit PC-Problem schickt aus DriverPilot einen **bereinigten Diagnosebericht** an
Christians Server. Christian sieht den Bericht in einer Admin-Ansicht, schreibt (oder lässt von
ChatGPT vorschreiben) eine Antwort mit Fakten, Vermutungen und konkreten manuellen Schritten
und **gibt sie frei**. DriverPilot zeigt dem Freund ausschließlich freigegebene Antworten an und
führt nichts davon selbst aus.

```
Freund (DriverPilot)  ──HTTPS──▶ driverpilot.cstrube.de ──▶ Server auf rpi4-400
                                                                 │
Christian (Browser)   ──LAN/Tailnet + Authentik──▶ Admin-Ansicht ┘   optional: ChatGPT-Entwurf
```

Was der Server **nicht** ist: kein Fernzugriff, keine Remote-Shell, keine Treiberinstallation auf
Serverbefehl, kein Dauerdienst auf dem PC des Freundes. Der Bericht enthält keine Gerätenamen,
Seriennummern, Pfade, Ereignistexte oder IP-Adressen; der Server lehnt Berichte ab, in denen so
etwas erkannt wird.

Ein Fall lebt **7 Tage** ab Eingang und wird dann automatisch gelöscht. Der Freund kann ihn
jederzeit vorher aus DriverPilot löschen.

---

## 2. Für Freunde: Hilfe anfordern

### 2.1 Was du brauchst

- DriverPilot in einer Version mit dem Bereich **Hilfe von Christian**.
- Von Christian: die **Serveradresse** `https://driverpilot.cstrube.de` und einen
  **Einladungscode** (32 Zeichen). Beides kommt per Nachricht von Christian, nicht aus dem Internet.
- Kein ChatGPT-Konto, kein Abo.

### 2.2 Koppeln (einmalig)

1. In DriverPilot **Hilfe von Christian** öffnen → **Koppeln**.
2. Serveradresse und Einladungscode eintragen, bestätigen.
3. DriverPilot bekommt einen Zugang, der **30 Tage** gilt. Der Code ist danach verbraucht
   (bei Mehrfachcodes: eine Einlösung weniger).

Wenn der Zugang abgelaufen ist oder Christian ihn widerrufen hat, meldet DriverPilot
„Zugang ungültig“. Dann einfach einen neuen Code bei Christian holen.

### 2.3 Bericht senden

1. **Frischen Scan** machen (höchstens 15 Minuten alt; sonst lehnt der Server ab).
2. Problem beschreiben: Kategorie wählen (WoW-Absturz, PC friert ein, Grafikreset, Leistung,
   Netzwerk, Addon-Fehler, Sonstiges), Beschreibung, optional Schritte zum Nachstellen und
   WoW-Angaben (Spielversion, nur in WoW oder auch anderswo, Addon-Test gemacht).
   Keine E-Mail-Adressen, Links, Dateipfade, Passwörter oder Seriennummern in den Text
   schreiben, sonst wird der Bericht abgelehnt.
3. **Vorschau** vollständig lesen. Genau das wird gesendet, nichts anderes.
4. **Datenschutzhinweis** lesen. Optional das Kästchen **externe KI erlauben** setzen: dann darf
   Christian den Bericht zusätzlich von ChatGPT (OpenAI) vorbewerten lassen. Ohne Haken
   bleibt der Bericht auf Christians Server.
5. **Zustimmen und senden**. Der Fall erscheint als „in Bearbeitung“.

Bei Fehlermeldungen: Abschnitt 6.

### 2.4 Antwort lesen

Solange der Bereich geöffnet ist, fragt DriverPilot den Server regelmäßig ab. Sobald Christian
freigegeben hat, erscheint die Antwort mit:

- **Zusammenfassung**
- **Fakten**: belegt durch Einträge deines Berichts.
- **Vermutungen**: ausdrücklich unbewiesen.
- **Nächste Schritte**: jeweils mit Begründung, Anleitung, Risikoklasse (nur lesen /
  rückgängig machbar / nur für Experten), benötigten Rechten, erwartetem Ergebnis und, wo
  möglich, Rückweg. Du führst sie selbst aus, DriverPilot tut nichts automatisch.
- **Rückfragen** und **Hinweise**, optional Quellenlinks (öffnen sich nur auf Klick).

Wenn du inzwischen einen neueren Scan gemacht hast, markiert DriverPilot die Antwort als zu einem
älteren Scan gehörig. Ein neues Problem oder ein Nachher-Vergleich = neuer Bericht (neuer Fall).

### 2.5 Rückmeldung und Löschen

- **Rückmeldung** zur Antwort: besser / unverändert / schlechter / nicht probiert, plus Notiz.
  Höchstens zehn je Fall. Löst keine neue KI-Anfrage aus.
- **Fall löschen**: entfernt Bericht, Entwürfe, Antworten und Rückmeldungen sofort vom Server.
  Was bereits an ChatGPT übermittelt wurde (nur mit deinem Haken), lässt sich dadurch nicht
  zurückholen.

---

## 3. Für Christian: Fälle bearbeiten

### 3.1 Zugang

Admin-Ansicht: **https://driverpilot.dns-prod-2.local.cstrube.de** (nur LAN oder Tailnet,
Anmeldung über Authentik, Gruppe `Homelab-Admins`). Aus dem Internet ist sie nicht erreichbar.

Menü: **Fälle** · **Einladungen** · **Zugänge** · **Audit** · **KI (ChatGPT)**. Rechts oben steht
der angemeldete Benutzer, die Server-UTC und der aktive Adapter.

### 3.2 Einladung erzeugen und weitergeben

1. **Einladungen** → Bezeichnung (z. B. Name des Freundes), Gültigkeit in Tagen, Anzahl
   Einlösungen → **Erzeugen**.
2. Der Code erscheint **genau einmal**. Zusammen mit der Serveradresse per sicherem Kanal
   (Signal, iMessage, persönlich) weitergeben. Nicht in GitHub-Issues, nicht per E-Mail an Listen.
3. Empfehlung: pro Freund ein Code mit 1 Einlösung, 1 bis 7 Tage. Für eine Gruppe ein Code mit
   z. B. 10 Einlösungen und 30 Tagen. Nicht mehr gebrauchte Codes **Widerrufen**.

Jede Einlösung erzeugt einen eigenen Zugang (30 Tage). Unter **Zugänge** siehst du alle Zugänge
mit Fallzahl und kannst einzelne **widerrufen**; das wirkt beim nächsten Request des Clients,
auch für bestehende Fälle.

### 3.3 Fallübersicht

**Fälle** zeigt Kennzahlen (offen, warten auf Prüfung, fehlgeschlagen, neue Fälle heute,
Zugänge, Aufträge, KI-Aufrufe) und die Liste aller nicht abgelaufenen Fälle mit Zustand:

| Zustand | Bedeutung | Was du tust |
|---|---|---|
| `queued` | wartet auf den KI-Worker (nur mit KI-Haken und aktivem Login) | nichts, oder **Manuell übernehmen** |
| `analyzing` | KI-Aufruf läuft (bis 300 s) | warten; Aktionen sind gesperrt |
| `awaiting_review` | wartet auf dich | Entwurf prüfen/schreiben, freigeben |
| `released` | Revision ist für den Freund sichtbar | ggf. neue Revision |
| `analysis_failed` | KI-Lauf gescheitert (Grund steht dabei) | **Manuell übernehmen** oder **KI-Neuversuch** |

### 3.4 Fallseite

Oben: IDs, Eingang, Ablauf, Zugang, App-Version, ob externe KI erlaubt ist, Versuche, Version.
Dann der Bericht in lesbarer Form: Symptom und Freitext, Hardware, Geräte (Modellkennung
Bus/Vendor/Product, Treiberversion, Problemcode), Befunde (Quelle, Ereignis-ID, Anzahl,
Zeitraum, Stufe, Gerät), Erfassungsstatus. **Alles außer `complete` im Erfassungsstatus heißt
Lücke, nicht „unauffällig“.** Unten als Ausklapper der rohe JSON-Bericht.

Aktionen oben:

- **Manuell übernehmen** (aus `queued` oder `analysis_failed`): entwertet einen offenen
  KI-Auftrag, Fall geht auf `awaiting_review`.
- **KI-Neuversuch (budgetiert)**: nur wenn der Freund externe KI erlaubt hat und der Adapter
  angemeldet ist. Zählt gegen das Tagesbudget.
- **Fall löschen**: alles weg, wie beim Löschen durch den Freund.

### 3.5 Entwurf schreiben oder prüfen

Der Bereich **Entwurf** zeigt entweder den **KI-ENTWURF** (orange Warnung: ungeprüft), deinen
zuletzt gespeicherten Entwurf oder eine leere Vorlage. Bearbeitet wird im JSON-Feld. Felder:

```json
{
  "summary": "Kurzfassung in 1–2000 Zeichen.",
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
  "warnings": ["Z. B.: kein BIOS-Update ohne Rücksprache."],
  "sources": [{"title": "Offizielle Seite", "url": "https://..."}]
}
```

Regeln, die der Server beim Speichern erzwingt:

- Jeder Fakt braucht mindestens einen Beleg: eine `finding`-/`device`-ID **aus diesem Bericht**
  oder einen Feldzeiger (`/hardware/...`, `/symptom/...`, `/collection/...`).
- Vermutungen haben `proven: false` und verweisen auf Fakt-IDs. Keine Prozentwerte.
- `risk_class`: `read_only` | `reversible_change` | `expert_only`.
  `required_privileges`: `none` | `standard_user` | `administrator`.
- Nur Text. Kein Markdown, kein HTML, keine Skripte oder Befehle. Quellen nur `https://`,
  ohne Port und Benutzerangabe, nur offizielle Hersteller-/Microsoft-/Blizzard-Seiten.
- Längen: summary 2000, Texte 1000, Anleitung 4000, Titel 200 Zeichen; Gesamtergebnis ≤ 64 KiB.

**Entwurf speichern und prüfen** validiert und zeigt Verstöße als Liste. Hinweise mit
„(Hinweis, keine Sperre)“ sind nur Warnungen (z. B. Textmarker). Das Kästchen „beruht auf
einem KI-Entwurf“ steuert die Herkunftsangabe im Ergebnis (`human` oder
`ai_assisted_human_reviewed`); bei einem bearbeiteten KI-Entwurf angehakt lassen.

### 3.6 Freigeben

**Revision N freigeben** erscheint, sobald ein gültiger Entwurf gespeichert ist und der Fall in
`awaiting_review` oder `released` steht. Nach Bestätigung:

- Die Revision ist **unveränderlich** und für den Freund sichtbar (gebunden an Fall-ID, Scan-ID
  und Berichts-Hash; der Client prüft das).
- Änderungen danach = neuen Entwurf speichern und als **Revision N+1** freigeben; bis dahin
  bleibt die alte sichtbar.
- Wurde der Fall zwischenzeitlich geändert (z. B. zweiter Browser-Tab), lehnt der Server mit
  „zwischenzeitlich geändert, Seite neu laden“ ab.

Unter **Freigegebene Revisionen** siehst du jede Revision so, wie der Freund sie bekommt.
**Rückmeldungen** des Freunds stehen darunter mit Bezug auf die Revision.

---

## 4. KI-Entwürfe über ChatGPT

### 4.1 Wie es funktioniert

Adapter `codex`: der Server spricht das ChatGPT-Backend über denselben OAuth-Weg wie die
Codex-CLI an, mit Christians persönlichem ChatGPT-Konto. Nur Fälle, bei denen der Freund
**externe KI erlaubt** hat, landen in der Warteschlange. Der Worker sendet den Bericht als reine
Daten mit festen Anweisungen (`store=false`), prüft die Antwort gegen Schema und Belegregeln
und legt sie als **KI-Entwurf** ab. Nichts davon geht ungeprüft an den Freund.

Grenzen: ein Aufruf gleichzeitig, höchstens zwei automatische Versuche je Fall, 300 s Timeout
je Versuch, Tagesbudget `DP_AI_DAILY_CALLS` (Default 10). Ein Timeout gilt als
„Ausgang unbekannt“ und wird **nicht** automatisch wiederholt (kein doppeltes Abrechnen); du
entscheidest per **KI-Neuversuch** oder **Manuell übernehmen**.

Gemessen am 2026-10-01: gpt-5.6-sol braucht für einen vollständigen Bericht etwa 2–3 Minuten
und rund 7.000 Tokens.

### 4.2 Seite „KI (ChatGPT)“

- **Status**: angemeldet?, Konto, Token-Ablauf (wird automatisch erneuert), letzter Fehler,
  Modell, ob die KI den Clients angeboten wird, Aufrufe heute.
- **Mit ChatGPT anmelden (Device-Code)**: Code wird angezeigt, auf
  `https://auth.openai.com/codex/device` eingeben, Seite neu laden. Gilt 15 Minuten.
- **auth.json übernehmen**: Inhalt einer `~/.codex/auth.json` einfügen (Alternative zum
  Device-Login; so wurde am 2026-10-01 der Token des Homelab-Dashboards übernommen).
- **Abmelden**: löscht die Tokendatei; der Server fällt sofort in den manuellen Modus.

Ohne Login meldet `/capabilities` `external_ai_offered=false`: DriverPilot blendet die
KI-Option aus, alle Fälle laufen manuell. Fälle, die vorher mit KI-Haken in `queued` standen,
bleiben dort, bis ein Login da ist oder du sie übernimmst.

### 4.3 Hinweise

- Dashboard und Ferndiagnose-Server teilen sich derzeit denselben Refresh-Token. Verliert
  einer der beiden die Anmeldung (Token-Rotation), Tokendatei neu kopieren oder hier einen
  eigenen Device-Login machen.
- In den ChatGPT-Kontoeinstellungen muss „Das Modell für alle verbessern“ aus sein; der
  Datenschutzhinweis sagt das so zu.
- Modell und Reasoning: `DP_CODEX_MODEL`, `DP_CODEX_REASONING` in `.env` (Neustart nötig).

---

## 5. Betrieb

### 5.1 Wo was liegt

| Was | Wo |
|---|---|
| Server | `rpi4-400` (10.0.30.3), Docker Compose, `~/driverpilot-server` (Clone von GitHub, read-only Deploy-Key) |
| Daten | `~/driverpilot-server/data/` (SQLite `driverpilot.sqlite3`, `server.secret`, `codex-auth.json`), uid 10001, 0700. **Nicht in Backups.** |
| Konfiguration | `~/driverpilot-server/.env` (Vorlage `.env.example`) |
| Öffentliche API | `https://driverpilot.cstrube.de/api/v1` ← Cloudflare (proxied, `records.tf`) ← TrueNAS-Traefik `dynamic/driverpilot.yml` (`cloudflare-only`, CrowdSec, Rate-Limit) ← `10.0.30.3:8140` |
| Admin | `https://driverpilot.dns-prod-2.local.cstrube.de` ← Pi-Traefik `~/traefik/data/config.yml` (`agent-secured` + `sso`) ← `10.0.30.3:8141` |
| Repo / Logbuch | `github.com/Madchristian/DriverPilot-Server`, `STATUS.md`; Auftrag DriverPilot Issue #19 |

### 5.2 Tägliche Handgriffe

```bash
ssh christian@10.0.30.3
cd ~/driverpilot-server
docker compose ps                        # healthy?
docker compose logs --since 1h           # keine Bodies/Tokens im Log
curl -s http://127.0.0.1:8140/readyz     # "ready" = DB schreibbar
curl -s http://127.0.0.1:8140/api/v1/capabilities | head -c 300
```

Von außen prüfen: `curl -s https://driverpilot.cstrube.de/api/v1/capabilities`.
Direkt am Origin ohne Cloudflare muss 403 kommen (Origin-Lock).

### 5.3 Update und Rollback

```bash
cd ~/driverpilot-server
git pull && docker compose up -d --build        # Update
git log --oneline -5
git checkout <alter-commit> && docker compose up -d --build   # Rollback
```

Das Datenbankschema wird nur ergänzt (`CREATE TABLE IF NOT EXISTS`), ein älterer Stand läuft
mit einer neueren Datenbank weiter. Ein Neustart verliert keine angenommenen Fälle; laufende
KI-Aufrufe werden beim Start als `analysis_failed` / `outcome_unknown` markiert.

### 5.4 Einstellungen in `.env`

| Variable | Bedeutung |
|---|---|
| `DP_API_TRUSTED_PROXIES` | Proxy, dessen `CF-Connecting-IP` für Rate-Limits zählt (`10.0.30.20`) |
| `DP_ADMIN_TRUSTED_PROXIES` | Proxys, deren Authentik-Header gelten (`10.0.30.5,10.0.20.162`; die Pi erreicht die .3 über VLAN20) |
| `DP_ADMIN_GROUP` | Authentik-Gruppe (`Homelab-Admins`) |
| `DP_PUBLIC_BASE_URL` | wird mit dem Einladungscode angezeigt |
| `DP_PRIVACY_NOTICE_VERSION` / `_FILE` | **bei jeder Textänderung Version anheben**; alte Zustimmungen werden abgelehnt, DriverPilot holt eine neue |
| `DP_AI_PROVIDER` | `none` / `test` / `codex` |
| `DP_CODEX_MODEL`, `DP_CODEX_REASONING` | Modellwahl |
| `DP_AI_DAILY_CALLS`, `DP_AI_TIMEOUT_SECONDS` | Budget und Timeout |
| `DP_MAX_NEW_CASES_PER_CLIENT_PER_DAY` (5), `DP_MAX_NEW_CASES_GLOBAL_PER_DAY` (30), `DP_MAX_OPEN_CASES_GLOBAL` (100), `DP_CLIENT_REQUESTS_PER_MINUTE` (30) | Limits; dürfen nur verschärft werden |

Änderungen wirken nach `docker compose up -d`.

### 5.5 Datenschutzhinweis ändern

1. `privacy_notice.txt` im Repo ändern (Empfänger, Zweck, KI-Anbieter, Löschfrist).
2. `DP_PRIVACY_NOTICE_VERSION` in `.env` auf einen neuen Wert (z. B. Datum.Zähler).
3. Commit, Push, auf der Pi `git pull && docker compose up -d --build`.

### 5.6 Bereinigung, Audit, Logs

- Stündlich: abgelaufene Fälle physisch löschen (SQLite `secure_delete` + WAL-Checkpoint),
  Tombstones nach Ablauf des Zugangs, Audit nach 30 Tagen, verbrauchte Einladungen.
- **Audit** (Admin-Seite): wer hat wann was mit welchem Fall gemacht; kein Berichtinhalt.
- Container-Log: Start/Stop, Worker, Warnungen; nie Bodies, Tokens, Einladungen oder
  Modellantworten. Codex-Aufrufe erscheinen nur als Länge/Tokenverbrauch.

### 5.7 Vertrag aktualisieren

Der Vertrag liegt unter `contract/v1` als byte-exakte Kopie aus dem DriverPilot-Repo
(`contract/CONTRACT_SOURCE` nennt den Commit). Änderungen immer zuerst dort per PR
abstimmen, dann `v1/` ersetzen, `CONTRACT_SOURCE` aktualisieren,
`.venv/bin/python contract/validate_contract.py contract/v1` und `pytest` laufen lassen.

---

## 6. Störungen und Fehlercodes

### 6.1 Was DriverPilot dem Freund meldet

| Code | Bedeutung | Abhilfe |
|---|---|---|
| `invitation_invalid` | Code unbekannt, abgelaufen, verbraucht oder widerrufen | neuen Code von Christian |
| `token_invalid` | Zugang fehlt, abgelaufen (30 Tage) oder widerrufen | neu koppeln mit neuem Code |
| `scan_too_old` | Scan älter als 15 Minuten | neuen Scan, erneut senden |
| `clock_skew` | PC-Uhr geht mehr als 5 Minuten vor | Datum/Uhrzeit am PC prüfen |
| `privacy_notice_outdated` | Hinweis wurde geändert | DriverPilot zeigt den neuen Text, erneut zustimmen |
| `text_rejected` | E-Mail, Link, Pfad, Passwort-/Seriennummer-Angabe o. ä. im Text | Text umformulieren |
| `daily_case_limit_reached` | 5 Fälle heute | morgen wieder |
| `capacity_exhausted` / `service_unavailable` | Server voll oder nicht bereit, nichts gespeichert | später erneut, ggf. Christian fragen |
| `rate_limited` | zu viele Anfragen | kurz warten (Retry-After) |
| `not_found` | Fall gelöscht, abgelaufen oder gehört nicht zu diesem Zugang | neuen Bericht senden |
| `schema_violation` / `unsupported_schema_version` | Client und Server passen nicht zusammen | DriverPilot aktualisieren, sonst Christian |

Eine Übersicht aller Codes: `contract/v1/errors.json`.

### 6.2 Typische Serverprobleme

| Symptom | Ursache | Abhilfe |
|---|---|---|
| Admin-Seite: „Zugriff verweigert“ trotz Authentik-Login | Request kommt nicht von einem Proxy in `DP_ADMIN_TRUSTED_PROXIES` oder Gruppe fehlt | `.env` prüfen; Pi-Routing (`ip route get 10.0.30.3` auf dns-prod-2) |
| `external_ai_offered=false` obwohl Adapter `codex` | nicht angemeldet oder Token-Refresh gescheitert | Seite „KI (ChatGPT)“: Status/letzter Fehler, neu anmelden |
| Fälle bleiben in `queued` | kein Login oder Worker steht | Login prüfen; `docker compose logs`; notfalls **Manuell übernehmen** |
| `analysis_failed` / `outcome_unknown` | Timeout (300 s) oder Neustart während des Aufrufs | **KI-Neuversuch** oder manuell |
| `analysis_failed` / `output_rejected` | Modellantwort verletzt Schema/Belege | manuell; Log zeigt Status/Content-Type, nie Inhalt |
| `analysis_failed` / `budget_exhausted` | Tagesbudget erreicht | morgen oder `DP_AI_DAILY_CALLS` erhöhen |
| `analysis_failed` / `provider_unavailable` | Netz/429/5xx bei OpenAI, 2 Versuche verbraucht | später **KI-Neuversuch** |
| `readyz` liefert `not ready` | Datenbank nicht schreibbar (Disk voll, Rechte) | `df -h`, Rechte von `data/` (uid 10001, 0700) |
| Von außen 403 | Request geht nicht über Cloudflare | DNS prüfen (`dig driverpilot.cstrube.de` → Cloudflare-IPs) |
| Von außen 522/524 | Traefik auf TrueNAS erreicht `10.0.30.3:8140` nicht | Container auf der Pi, `docker compose ps`; Traefik-Datei `dynamic/driverpilot.yml` |

### 6.3 Notfall: alles aus

```bash
cd ~/driverpilot-server && docker compose down     # API und Admin sofort weg, Daten bleiben in data/
```

Öffentliche Route still legen: auf der TrueNAS `dynamic/driverpilot.yml` umbenennen
(Traefik lädt das Verzeichnis live). Einladungen und Zugänge lassen sich jederzeit in der
Admin-Ansicht widerrufen.
