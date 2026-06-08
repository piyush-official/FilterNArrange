# syntax=docker/dockerfile:1.7

# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
RUN npm run build

# ---- runtime stage ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
# busybox wget on alpine resolves ``localhost`` to ::1 first, but nginx only
# listens on 0.0.0.0:80 (the upstream nginx:alpine entrypoint adds the IPv6
# listen only when conf.d/default.conf is in use, which our global override
# bypasses). Pin to 127.0.0.1 so the healthcheck doesn't false-negative.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD wget -qO- http://127.0.0.1/health >/dev/null || exit 1
