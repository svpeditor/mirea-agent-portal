FROM node:20-alpine

WORKDIR /agent

# Этот Dockerfile НЕ используется порталом для сборки — портал генерирует
# свой Dockerfile из manifest.yaml (см. apps/portal-worker/portal_worker/
# builder/dockerfile_gen.py), инжектит @mirea/portal-sdk и собирает образ.
# Этот файл — для local-dev.

COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

COPY agent.js manifest.yaml ./

ENTRYPOINT ["node", "agent.js"]
