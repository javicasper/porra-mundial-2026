#!/bin/sh
# Auto-crónicas: cuando una ronda de eliminatoria termina y aún no tiene crónica,
# la genera con Claude (engine/generar_noticia.py). Pensado para cron.
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin
REPO=/root/porra2026
LOG=/var/log/porra-noticias.log
cd "$REPO" || exit 1
[ -f web/data.json ] || exit 0

# Candado: una sola generación a la vez (una crónica con muchos memes puede tardar).
LOCK=/tmp/porra-noticias.lock
mkdir "$LOCK" 2>/dev/null || exit 0
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

# id:FaseEnPartidos:nº_partidos_de_la_ronda
for spec in dieciseisavos:Dieciseisavos:16 octavos:Octavos:8 cuartos:Cuartos:4 semifinales:Semifinales:2; do
  id=${spec%%:*}; rest=${spec#*:}; name=${rest%%:*}; n=${rest##*:}
  # ¿ya existe la crónica?
  grep -q "\"id\": \"$id\"" web/noticias.json 2>/dev/null && continue
  # ¿ronda completa? (todos sus partidos jugados)
  done=$(python3 -c "import json;d=json.load(open('web/data.json'));print(sum(1 for p in d['partidos'] if p.get('fase')=='$name' and p.get('jugado') and p.get('golesLocal') is not None))" 2>/dev/null)
  [ -z "$done" ] && continue
  if [ "$done" -ge "$n" ]; then
    echo "$(date -u '+%F %T') ronda $name completa ($done/$n) -> generando crónica" >> "$LOG"
    python3 engine/generar_noticia.py "$id" >> "$LOG" 2>&1 && echo "$(date -u '+%F %T') OK $id" >> "$LOG"
  fi
done
