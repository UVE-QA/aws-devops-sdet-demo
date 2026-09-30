# The web service (ADR-0095): nginx serving the static interface that the api
# used to serve from its own `/`. Nothing else - no server-side rendering, no
# calls to the api from here. The browser calls /api/* on the same origin, and
# the load balancer routes it; locally, Compose mounts a proxy into conf.d/local.
# FROM ECR PUBLIC, NOT DOCKER HUB (2026-09-14). Two builds in one night on
# GitHub's runners died in two seconds on `failed to fetch oauth token: Post
# https://auth.docker.io/token: connection reset by peer` - the first public
# launch after ADR-0100 and the image scan on the fix for it. The image is
# the same official one, mirrored by AWS at public.ecr.aws/docker/library,
# pulled without Docker Hub's token dance - and, since 2026-09-30, signed in:
# ECR Public's anonymous limit is per IP address, and the runners share theirs.
# 1.29, NOT 1.27 (2026-09-30). The first scan that could pull the image again
# found HIGH OpenSSL fixes that 1.27-alpine's Alpine 3.21 does not carry yet;
# 1.28-alpine took them and was left with five HIGH nginx CVEs that Alpine
# patches in its own package and nginx.org's does not. The mainline 1.29
# scans clean. nginx calls mainline the branch for general use.
FROM public.ecr.aws/docker/library/nginx:1.29-alpine

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
