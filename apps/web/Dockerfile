FROM node:24-alpine

WORKDIR /app

# Dependencias primero (capa de caché).
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# `API_URL` se evalúa también al construir (rewrites de next.config.ts).
ARG API_URL=http://localhost:8101
ENV API_URL=${API_URL} \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

RUN npm run build

# Usuario sin privilegios (§18.3): `next start` no escribe en disco.
# Imagen Alpine: `adduser` busybox, no `useradd`.
RUN addgroup -S nextjs && adduser -S nextjs -G nextjs \
    && chown -R nextjs:nextjs /app
USER nextjs

EXPOSE 8100

CMD ["npm", "run", "start"]
