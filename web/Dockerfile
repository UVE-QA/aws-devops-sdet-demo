# The web service (ADR-0095): nginx serving the static interface that the api
# used to serve from its own `/`. Nothing else - no server-side rendering, no
# calls to the api from here. The browser calls /api/* on the same origin, and
# the load balancer routes it; locally, Compose mounts a proxy into conf.d/local.
FROM nginx:1.27-alpine

# Take the distribution's fixes at build time, for the reason app/Dockerfile
# gives: the base tag lags its distribution, and the image scan gates on what
# has a fix available.
RUN apk upgrade --no-cache

# The one server block, in place of the image's default.
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Compose mounts a proxy for /api here; in AWS the directory is empty and the
# load balancer does the routing. The directory exists so the include can be
# a glob over nothing rather than a path that is not there.
RUN mkdir -p /etc/nginx/conf.d/local

COPY static/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/healthz >/dev/null 2>&1 || exit 1
