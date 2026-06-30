#!/bin/sh
# Auto-crónicas de eliminatoria (El Salseo). Genera la mini-crónica de cada partido
# jugado que aún no tenga y, al cerrar una ronda, la crónica general. Pensado para cron.
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin
# codex vive en el bin de nvm; añadirlo para que la generación de memes funcione en cron
for nb in /root/.nvm/versions/node/*/bin; do PATH="$PATH:$nb"; done
REPO=/root/porra2026
LOG=/var/log/porra-noticias.log
cd "$REPO" || exit 1
[ -f web/data.json ] || exit 0

# Candado: una sola generación a la vez (una crónica con memes puede tardar bastante).
LOCK=/tmp/porra-noticias.lock
mkdir "$LOCK" 2>/dev/null || exit 0
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

echo "$(date -u '+%F %T') auto" >> "$LOG"
python3 engine/generar_noticia.py auto >> "$LOG" 2>&1
