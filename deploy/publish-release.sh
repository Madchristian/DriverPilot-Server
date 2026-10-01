#!/usr/bin/env bash
# Laedt die Dateien eines DriverPilot-Releases herunter, prueft sie gegen SHA256SUMS.txt und
# kopiert sie in das Download-Verzeichnis des Ferndiagnose-Servers auf rpi4-400.
#
# Laeuft auf dns-prod-2 (gh ist dort mit Zugriff auf das private Repo eingerichtet):
#   deploy/publish-release.sh v0.3.4
#
# Aeltere Dateien bleiben liegen; wer sie entfernen will, loescht sie auf der Pi in
# ~/driverpilot-server/downloads/. Die Seite /downloads/ liest das Verzeichnis live.
set -euo pipefail

TAG="${1:?Release-Tag angeben, z.B. v0.3.4}"
REPO="${DP_CLIENT_REPO:-Madchristian/DriverPilot}"
TARGET="${DP_DOWNLOADS_TARGET:-christian@10.0.30.3:driverpilot-server/downloads/}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "Lade $REPO $TAG ..."
gh release download "$TAG" --repo "$REPO" --dir "$WORK" --clobber
cd "$WORK"
if [ ! -f SHA256SUMS.txt ]; then
  echo "SHA256SUMS.txt fehlt im Release; Abbruch." >&2
  exit 1
fi
sha256sum -c SHA256SUMS.txt
ls -l

echo "Kopiere nach $TARGET ..."
scp -q ./* "$TARGET"
echo "Fertig. Pruefen: https://driverpilot.cstrube.de/downloads/"
