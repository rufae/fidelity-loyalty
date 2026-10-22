FROM python:3.12-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.11.17 /uv /uvx /bin/

WORKDIR /app

# Dependencias primero (capa de caché): solo las de runtime.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

# Usuario sin privilegios (§18.3): la API no necesita escribir nada en disco.
# Las migraciones corren contra PostgreSQL, no contra ficheros locales.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8101

# Migraciones antes de arrancar: la API nunca sirve con un esquema desactualizado.
# `--forwarded-allow-ips`: sólo se confía en `X-Forwarded-For` cuando la
# petición llega desde un proxy interno (loopback o redes privadas). Con '*'
# cualquiera con acceso de red al puerto falseaba su IP y anulaba los límites
# antiabuso. En producción el puerto de la API se publica además en loopback
# (API_PORT=127.0.0.1:8101), así que ningún cliente externo lo alcanza.
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && \
     uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8101 \
     --proxy-headers --forwarded-allow-ips='127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10'"]
