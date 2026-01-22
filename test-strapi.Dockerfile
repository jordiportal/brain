FROM node:20-alpine

RUN apk add --no-cache \
    build-base \
    gcc \
    autoconf \
    automake \
    libc6-compat \
    wget

WORKDIR /srv/app

# Crear proyecto Strapi con la última versión
RUN npx create-strapi-app@latest . \
    --quickstart \
    --no-run \
    --typescript

EXPOSE 1337

CMD ["npm", "run", "develop"]
