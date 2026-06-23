#!/bin/sh
# Despliegue invocado por GitHub Actions vía SSH (clave restringida a ESTE script).
# Baja origin/master, re-ejecuta los tests con los datos REALES y, si pasan, queda
# desplegado (web/ va por volumen y porra-refresh ejecuta el repo). Si los tests
# fallan, revierte. Recompone Docker solo si cambió la infraestructura.
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
REPO=/root/porra2026
LOG=/var/log/porra-deploy.log
cd "$REPO" || exit 1

log(){ echo "$(date -u '+%F %T') $*" | tee -a "$LOG"; }

old=$(git rev-parse HEAD)
git fetch -q origin master 2>>"$LOG" || { log "ERROR fetch"; exit 1; }
new=$(git rev-parse origin/master)
if [ "$old" = "$new" ]; then log "sin cambios ($(git rev-parse --short HEAD))"; exit 0; fi

log "desplegando $(git rev-parse --short "$old") -> $(git rev-parse --short "$new")"
git reset --hard origin/master >>"$LOG" 2>&1

if ! python3 engine/test_motor.py >>"$LOG" 2>&1 || ! python3 engine/test_ko.py >>"$LOG" 2>&1; then
  log "ERROR tests fallan con datos reales -> ROLLBACK a $(git rev-parse --short "$old")"
  git reset --hard "$old" >>"$LOG" 2>&1
  exit 1
fi

# Recomponer solo si cambió la infraestructura
if git diff --name-only "$old" "$new" | grep -qE '^(docker-compose\.yml|deploy/)'; then
  # --force-recreate: los mounts de fichero suelto (nginx.conf) no se refrescan
  # con un 'up -d' normal tras git reset (cambia el inodo); recrear sí los re-monta.
  log "infra cambiada -> docker compose up -d --force-recreate"
  docker compose -f "$REPO/docker-compose.yml" up -d --force-recreate >>"$LOG" 2>&1
fi
log "OK desplegado $(git rev-parse --short HEAD)"
