FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
ARG FRONTEND_BUILD_STAMP=1
COPY . .
RUN npm run build

# ── Dev runtime (default) — serves on port 3000 via nginx.conf ───────────────
FROM nginx:alpine AS dev-runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000

# ── Production runtime — serves on port 80 via nginx.prod.conf ───────────────
FROM nginx:alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.prod.conf /etc/nginx/nginx.conf
EXPOSE 80
