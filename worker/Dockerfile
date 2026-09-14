# The worker (Phase 42, ADR-0096): consumes `item.created` from SQS and stamps
# the row. Its own image, its own dependencies, none of the api's code - the
# two share a database today and a message contract always, and the second is
# what plan item 4 keeps.
# FROM ECR PUBLIC, NOT DOCKER HUB (2026-09-14). Two builds in one night on
# GitHub's runners died in two seconds on `failed to fetch oauth token: Post
# https://auth.docker.io/token: connection reset by peer` - the first public
# launch after ADR-0100 and the image scan on the fix for it. The image is
# the same official one, mirrored by AWS at public.ecr.aws/docker/library,
# pulled anonymously without Docker Hub's token dance or its rate limit.
FROM public.ecr.aws/docker/library/python:3.12-slim

# Debian's fixes at build time, for the reason app/Dockerfile gives.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

#   /app/consumer   -> the package (python -m consumer.main)
#   /app/alembic    -> the worker's own migrations (alembic upgrade head)
#   /app/scripts    -> sqs_tool.py, the break test's hands
COPY alembic.ini ./
COPY alembic ./alembic
COPY consumer ./consumer
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# No port. The container's health is the heartbeat file the loop touches on
# every pass - see consumer/main.py - and the task definition asks about it.
CMD ["python", "-m", "consumer.main"]
