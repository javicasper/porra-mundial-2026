#!/bin/sh
# Auto-deploy: si hay nuevos commits en origin/master, los trae y despliega.
# Pensado para cron (cada minuto). El despliegue es "vivo": nginx sirve web/ por
# volumen y porra-refresh ejecuta el código del repo, así que basta con el pull.
# Solo recompone Docker si cambian docker-compose.yml o deploy/. Hace fast-forward
# (no pisa cambios locales sin commitear; si no puede, lo registra y sale).
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
REPO=/root/porra2026
LOG=/var/log/porra-deploy.log
cd "$REPO" || exit 1

git fetch -q origin master 2>>"$LOG" || exit 0
before=$(git rev-parse HEAD)
after=$(git rev-parse origin/master)
[ "$before" = "$after" ] && exit 0          # nada nuevo

if ! git merge --ff-only origin/master >/dev/null 2>&1; then
  echo "$(date -u '+%F %T') WARN no fast-forward (cambios locales sin commitear?), saltando" >>"$LOG"
  exit 0
fi
echo "$(date -u '+%F %T') deploy $(git rev-parse --short "$before") -> $(git rev-parse --short "$after")" >>"$LOG"

# Recomponer solo si cambió la infraestructura
if git diff --name-only "$before" "$after" | grep -qE '^(docker-compose\.yml|deploy/)'; then
  echo "$(date -u '+%F %T') infra cambiada -> docker compose up -d" >>"$LOG"
  docker compose -f "$REPO/docker-compose.yml" up -d >>"$LOG" 2>&1
fi
