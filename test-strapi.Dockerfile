FROM node:20-alpine

RUN apk add --no-cache \
    build-base \
    gcc \
    autoconf \
    automake \
    libc6-compat \
    wget

WORKDIR /srv/app

# Crear proyecto Strapi vanilla con SQLite (más simple)
RUN yes n | npx create-strapi-app@latest . \
    --quickstart \
    --no-run \
    --skip-cloud \
    --typescript || true

EXPOSE 1337
EXPOSE 5173

CMD ["npm", "run", "develop"]
