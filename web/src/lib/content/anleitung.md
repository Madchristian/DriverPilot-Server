# DriverPilot: Anleitung für Freunde

DriverPilot ist ein Windows-Programm von Christian, das Hardware und Treiber deines PCs im Blick
behält. Mit „Hilfe von Christian“ kannst du ihm bei einem konkreten Problem einen bereinigten
Diagnosebericht schicken. Er sieht sich den Bericht an und schreibt dir eine Antwort mit
Fakten, Vermutungen und Schritten, die du selbst ausführst. DriverPilot ändert nichts an deinem
PC auf Anweisung von außen.

## 1. Installation

Die Dateien findest du unter [Downloads](/downloads/). Für die Installation nimmst du die
Setup-ZIP, `DriverPilot-<Version>-Setup-x64.zip`. Sie enthält die Setup-Datei, das Zertifikat
`DriverPilot.cer` und die `ZERTIFIKAT-ANLEITUNG.txt`. Die Setup-EXE gibt es auch einzeln, aber
Browser und Microsoft Defender SmartScreen blockieren den direkten Download einer EXE, die noch
nicht viele Leute heruntergeladen haben. Die ZIP kommt durch. Die portable ZIP
(`DriverPilot-<Version>-win-x64.zip`) ist die Variante ohne Installation und ohne
Wartungsautomatik.

Die Programme sind mit Christians eigenem Zertifikat signiert. Windows kennt dieses Zertifikat
nicht von sich aus, darum richtest du das Vertrauen einmalig selbst ein:

1. Die Setup-ZIP in einen eigenen Ordner entpacken (Rechtsklick, „Alle extrahieren“).
2. Den SHA-256-Fingerabdruck aus `ZERTIFIKAT-ANLEITUNG.txt` direkt mit Christian abgleichen,
   zum Beispiel am Telefon. Eine Anleitung und ein Zertifikat aus derselben Downloadquelle
   beweisen allein nicht, dass die Quelle unverändert ist.
3. Im entpackten Ordner PowerShell öffnen und prüfen: `Get-FileHash .\DriverPilot.cer -Algorithm SHA256`.
   Nur weitermachen, wenn der Fingerabdruck genau passt.
4. `DriverPilot.cer` doppelklicken, „Zertifikat installieren“, „Lokaler Computer“, „Alle
   Zertifikate in folgendem Speicher speichern“, „Vertrauenswürdige Stammzertifizierungsstellen“,
   „Fertig stellen“. Windows fragt nach Administratorrechten und zeigt eventuell eine Warnung.
5. Die Setup-Datei mit der rechten Maustaste anklicken, „Eigenschaften“, „Digitale
   Signaturen“, „Christian Strube“, „Details“. Windows muss die Signatur als gültig anzeigen.
6. Setup starten. Zeigt SmartScreen „Der Computer wurde durch Windows geschützt“, dann erst
   „Weitere Informationen“ und „Trotzdem ausführen“, wenn Schritt 5 eine gültige Signatur von
   Christian Strube gezeigt hat. Das Setup kopiert DriverPilot nach `C:\Program Files\DriverPilot`
   und richtet die Wartungsautomatik ein; du kannst sie in den Einstellungen abschalten.

Meldet Microsoft Defender dagegen einen Virenfund mit Namen (etwa „Trojan:…“ oder „Wacatac“)
oder verschiebt die Datei in die Quarantäne, die Datei nicht freigeben. Sag Christian Bescheid,
mit dem Namen aus der Meldung. Bei selbst signierten Installern kommt das als Fehlalarm vor;
Christian klärt das mit Microsoft.

Windows-Schutzfunktionen bleiben an. Weder das Setup noch die App importieren Zertifikate von
selbst. Updates einer installierten Version machst du über „Einstellungen“ und „Updatepaket
auswählen“ mit der portablen ZIP einer neueren Version.

Die Funktion „Hilfe von Christian“ ist in Version 0.3.4 noch nicht enthalten. Sie kommt mit
der nächsten Version; die Downloadseite zeigt immer die aktuelle.

## 2. Was du für die Ferndiagnose brauchst

Von Christian bekommst du einen Einladungslink. Die Seite dahinter zeigt dir die Serveradresse
`https://driverpilot.cstrube.de` und deinen Einladungscode mit Knöpfen zum Kopieren. Hat dir
Christian stattdessen Adresse und Code direkt geschickt, geht das genauso. Ein ChatGPT-Konto
brauchst du nicht.

## 3. Koppeln (einmalig)

1. In DriverPilot „Hilfe von Christian“ öffnen und auf „Koppeln“ gehen.
2. Serveradresse und Einladungscode von der Einladungsseite kopieren, eintragen und bestätigen.
3. DriverPilot bekommt einen Zugang, der 30 Tage gilt. Der Code ist danach verbraucht.

Ist der Zugang abgelaufen oder hat Christian ihn widerrufen, meldet DriverPilot „Zugang
ungültig“. Dann holst du dir einen neuen Code bei Christian.

## 4. Bericht senden

1. Einen frischen Scan machen. Er darf höchstens 15 Minuten alt sein.
2. Das Problem beschreiben: Kategorie wählen (WoW-Absturz, PC friert ein, Grafikreset,
   Leistung, Netzwerk, Addon-Fehler, Sonstiges) und eine Beschreibung schreiben. Schritte zum
   Nachstellen und WoW-Angaben sind freiwillig. E-Mail-Adressen, Links, Dateipfade, Passwörter
   oder Seriennummern gehören nicht in den Text, sonst wird der Bericht abgelehnt.
3. Die Vorschau vollständig lesen. Genau das wird gesendet, sonst nichts.
4. Den [Datenschutzhinweis](/datenschutz) lesen. Wenn du das Kästchen „externe KI erlauben“
   setzt, darf Christian den Bericht zusätzlich von ChatGPT (OpenAI) vorbewerten lassen. Ohne
   Haken bleibt der Bericht auf Christians Server.
5. „Zustimmen und senden“.

Was im Bericht steht: ausgewählte Hardwarefelder (Windows-Version, CPU, RAM, Mainboard, BIOS),
höchstens 64 Geräte mit bereinigter Modellkennung und Treiberversion, höchstens 200 gruppierte
Systemereignisse der letzten 24 Stunden (Quelle, Ereignisnummer, Anzahl, Zeitraum) und dein
eigener Text. Keine Gerätenamen, Seriennummern, Dateipfade, Ereignistexte, Benutzernamen oder
IP-Adressen.

## 5. Antwort lesen

Solange der Bereich geöffnet ist, fragt DriverPilot den Server regelmäßig ab. Sobald Christian
freigegeben hat, siehst du die Antwort: eine Zusammenfassung, Fakten mit Belegen aus deinem
Bericht, Vermutungen, die ausdrücklich unbewiesen sind, und nächste Schritte. Jeder Schritt hat
eine Begründung, eine Anleitung, eine Risikoklasse (nur lesen, rückgängig machbar, nur für
Experten), die benötigten Rechte, das erwartete Ergebnis und, wo möglich, einen Rückweg. Du
führst die Schritte selbst aus. Links in der Antwort öffnen sich nur auf Klick.

Hast du inzwischen einen neueren Scan gemacht, markiert DriverPilot die Antwort als zu einem
älteren Scan gehörig. Für ein neues Problem schickst du einen neuen Bericht.

## 6. Rückmeldung und Löschen

Zu einer Antwort kannst du eine Rückmeldung geben (besser, unverändert, schlechter, nicht
probiert) und eine Notiz dazu schreiben, höchstens zehn je Fall.

„Fall löschen“ entfernt Bericht und Antworten sofort vom Server. Spätestens 7 Tage nach dem
Senden löscht der Server den Fall von selbst. Was mit deinem Haken bereits an ChatGPT
übermittelt wurde, holt das Löschen nicht zurück.

## 7. Fehlermeldungen

| Meldung | Bedeutung | Was du tun kannst |
|---|---|---|
| Einladung ungültig | Code unbekannt, abgelaufen, verbraucht oder widerrufen | neuen Code von Christian |
| Zugang ungültig | Zugang nach 30 Tagen abgelaufen oder widerrufen | mit neuem Code neu koppeln |
| Scan zu alt | Scan älter als 15 Minuten | neuen Scan, erneut senden |
| Uhr weicht ab | die PC-Uhr geht mehr als 5 Minuten vor | Datum und Uhrzeit prüfen |
| Datenschutzhinweis geändert | der Hinweis hat eine neue Version | neuen Text lesen, erneut zustimmen |
| Text abgelehnt | E-Mail, Link, Pfad, Passwort- oder Seriennummernangabe im Text | Text umformulieren |
| Tageslimit | heute schon 5 Berichte | morgen wieder |
| Server nimmt nichts an | Server voll oder nicht bereit, es wurde nichts gespeichert | später erneut, sonst Christian fragen |
| Zu viele Anfragen | Anfragelimit | kurz warten |
| Fall nicht vorhanden | gelöscht, abgelaufen oder gehört nicht zu diesem Zugang | neuen Bericht senden |
| Version passt nicht | DriverPilot und Server passen nicht zusammen | DriverPilot aktualisieren, sonst Christian |

Bei allem anderen: Christian fragen. Ohne Server funktioniert in DriverPilot weiterhin der
lokale Dateiexport, mit dem du den Bericht als Datei speichern und auf eigenem Weg weitergeben
kannst.
