"""Minting a GitHub App installation token, and dispatching one workflow.

This is the half of the project where the direction of trust reverses. Every
other path has GitHub authenticating to AWS through OIDC with no static key;
here AWS authenticates to GitHub, where no OIDC exists (ADR-0034). So:

  - the App's PEM lives in Secrets Manager, read by one role
  - the JWT it signs is valid for ten minutes
  - the installation token minted from it expires in one hour, carries exactly
    one permission (`actions: write`) on exactly one installation, and is
    discarded when this request ends

urllib rather than `requests`: two calls, and one less vendored dependency in a
package that already has to carry a crypto library.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import jwt

API = "https://api.github.com"
USER_AGENT = "aws-devops-sdet-demo-self-service"


class GitHubError(Exception):
    """A GitHub call failed. The message is safe to log and NEVER holds a token."""


def _request(method: str, url: str, token: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", USER_AGENT)
    if data is not None:
        request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read().decode() or "{}"
            return response.status, json.loads(payload)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:400]
        raise GitHubError(f"{method} {url.replace(API, '')} -> {exc.code}: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise GitHubError(f"{method} {url.replace(API, '')} -> {type(exc).__name__}") from exc


def app_jwt(app_id: str, private_key_pem: str, now: int) -> str:
    """RS256, ten minutes, backdated 60s for clock skew - GitHub's own guidance."""
    return jwt.encode(
        {"iat": now - 60, "exp": now + 600, "iss": str(app_id)},
        private_key_pem,
        algorithm="RS256",
    )


def installation_token(app_id: str, private_key_pem: str, installation_id: str, now: int) -> str:
    _, body = _request(
        "POST",
        f"{API}/app/installations/{installation_id}/access_tokens",
        app_jwt(app_id, private_key_pem, now),
    )
    token = body.get("token")
    if not token:
        raise GitHubError("installation token response carried no token")
    return token


def dispatch_workflow(token: str, owner: str, repo: str, workflow: str, ref: str, inputs: dict) -> None:
    """`workflow_dispatch`, and nothing else.

    `repository_dispatch` was rejected: it needs `contents: write`, strictly
    wider than the one thing this does, and its payload never appears in the
    run's UI. A 204 is the whole success case - the dispatch endpoint returns no
    run id, which is why the run has to carry the launch id in its NAME for the
    dashboard to find it (ADR-0026, ADR-0034).
    """
    status, _ = _request(
        "POST",
        f"{API}/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches",
        token,
        {"ref": ref, "inputs": inputs},
    )
    if status != 204:
        raise GitHubError(f"dispatch returned {status}, expected 204")
