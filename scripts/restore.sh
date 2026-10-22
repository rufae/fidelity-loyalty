#!/usr/bin/env bash
# Restauración de una copia de seguridad (AGENTS.md §20.3, §27 DEPLOYMENT).
#
# Uso:
#   scripts/restore.sh <fichero.dump> [base_destino] [--yes]
#
# - Por defecto restaura en la base de datos principal: pide confirmación
#   (`--yes` para automatizar). Las migraciones se re-aplican después si el
#   esquema es anterior (`alembic upgrade head` lo hace el backend al arrancar).
# - Con un nombre de base distinto, restaura allí sin confirmación: es la forma
#   de **probar** una copia sin tocar datos reales (recomendado, §20.3).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

POSTGRES_USER="${POSTGRES_USER:-localai}"
POSTGRES_DB="${POSTGRES_DB:-localai_fidelity}"

FILE="${1:-}"
if [ -z "$FILE" ]; then
  echo "Uso: scripts/restore.sh <fichero.dump> [base_destino] [--yes]" >&2
  exit 2
fi
if [ ! -s "$FILE" ]; then
  echo "✗ No existe el fichero de copia: $FILE" >&2
  exit 2
fi

TARGET_DB="${2:-$POSTGRES_DB}"
ASSUME_YES="no"
for ARG in "$@"; do
  if [ "$ARG" = "--yes" ]; then ASSUME_YES="yes"; fi
done

if [ "$TARGET_DB" = "$POSTGRES_DB" ] && [ "$ASSUME_YES" != "yes" ]; then
  echo "⚠ Restaurar en la base principal ($TARGET_DB) SOBRESCRIBE sus datos."
  echo "  Si solo quieres probar la copia, usa otro nombre de base:"
  echo "    scripts/restore.sh $FILE ${POSTGRES_DB}_restore_check"
  read -r -p "¿Continuar con la restauración en $TARGET_DB? [s/N] " ANSWER
  case "$ANSWER" in
    s|S|si|sí) ;;
    *) echo "Cancelado."; exit 3 ;;
  esac
fi

echo "→ Creando base $TARGET_DB si no existe"
docker compose exec -T db psql --username "$POSTGRES_USER" --dbname postgres \
  --command "CREATE DATABASE \"$TARGET_DB\"" >/dev/null 2>&1 || true

echo "→ Restaurando $FILE en $TARGET_DB"
docker compose exec -T db pg_restore \
  --username "$POSTGRES_USER" \
  --dbname "$TARGET_DB" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --exit-on-error \
  <"$FILE"

echo "✓ Restauración completada en $TARGET_DB"
