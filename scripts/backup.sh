#!/usr/bin/env bash
# Copia de seguridad de la base de datos (AGENTS.md §18.4).
#
# Uso:
#   scripts/backup.sh [directorio_salida]
#
# Genera un volcado en formato custom de PostgreSQL (`pg_restore` puede
# restaurarlo por objeto) comprimido por gzip, con marca de tiempo, y conserva
# los últimos BACKUP_KEEP volcados. Sale con error si no puede escribir: una
# copia que «parece» hecha es peor que un fallo ruidoso.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Valores por defecto = mismos defaults del docker-compose.
POSTGRES_USER="${POSTGRES_USER:-localai}"
POSTGRES_DB="${POSTGRES_DB:-localai_fidelity}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"

OUT_DIR="${1:-$REPO_ROOT/backup}"
mkdir -p "$OUT_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="$OUT_DIR/${POSTGRES_DB}_${STAMP}.dump"

echo "→ Volcando $POSTGRES_DB en $FILE"
docker compose exec -T db pg_dump \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --format=custom \
  --compress=6 \
  --no-owner \
  --no-privileges \
  >"$FILE"

# Verificación mínima: un fichero vacío no es una copia.
if [ ! -s "$FILE" ]; then
  echo "✗ El volcado está vacío: revisa que el contenedor 'db' esté levantado" >&2
  rm -f "$FILE"
  exit 1
fi

# Verificación de integridad (§18.4): pg_restore lee el índice del volcado.
# Aunque no esté vacío, un fichero truncado a mitad de la escritura restauraría
# a medias: esto falla ruidosamente antes de podar la copia anterior.
if ! docker compose exec -T db pg_restore --list <"$FILE" >/dev/null 2>&1; then
  echo "✗ El volcado no supera la verificación con pg_restore --list: se descarta" >&2
  rm -f "$FILE"
  exit 1
fi

echo "✓ $(du -h "$FILE" | cut -f1) escritos en $FILE"

# Poda de volcados antiguos (solo de esta base): se conservan los más recientes.
mapfile -t FILES < <(ls -1t "$OUT_DIR"/"${POSTGRES_DB}"_*.dump 2>/dev/null || true)
if [ "${#FILES[@]}" -gt "$BACKUP_KEEP" ]; then
  for OLD in "${FILES[@]:$BACKUP_KEEP}"; do
    echo "· podando copia antigua: $(basename "$OLD")"
    rm -f "$OLD"
  done
fi

echo "Listo. Restauración de prueba: scripts/restore.sh $FILE <otra_bd>"
