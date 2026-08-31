# Frontend Dockerfile for LossGraph
# Multi-stage build for optimized production image

FROM node:18-alpine as base

WORKDIR /app

# Development stage
FROM base as development

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]

# Production build stage
FROM base as builder

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build

# Production runtime stage
FROM node:18-alpine as production

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=5 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

CMD ["npm", "start"]
