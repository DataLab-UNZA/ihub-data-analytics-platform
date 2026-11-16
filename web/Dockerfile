# Image for the iHub Next.js front end, the only public container of the Cloud Run
# service. It calls the research API sidecar on localhost (IHUB_API_URL) from the
# server only. Built from the web/ directory by .github/workflows/deploy.yml.
# See docs/DEPLOYMENT.md and ADR-007.
ARG NODE_VERSION=20-slim

# 1. Install dependencies exactly as locked.
FROM node:${NODE_VERSION} AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# 2. Build the standalone server (next.config.mjs sets output: 'standalone').
FROM node:${NODE_VERSION} AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# 3. Run only the traced server files, as a non-root user.
FROM node:${NODE_VERSION} AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=8080 \
    IHUB_API_URL=http://127.0.0.1:8000

COPY --from=builder --chown=node:node /app/public ./public
RUN mkdir .next && chown node:node .next
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 8080
CMD ["node", "server.js"]
