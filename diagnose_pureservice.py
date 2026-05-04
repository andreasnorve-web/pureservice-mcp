"""Pureservice URL discovery + auth diagnosis.

Tries multiple combinations of (subdomain, path prefix, auth header) to
figure out exactly where the API lives for this tenant.

Usage:
    $env:PURESERVICE_API_KEY = "your-key"
    py diagnose_pureservice.py

Optional override:
    $env:PURESERVICE_HOST = "support.vanylven.no"   # if you know the host
"""
from __future__ import annotations

import os
import sys

import httpx

API_KEY = os.environ.get("PURESERVICE_API_KEY", "")
EXPLICIT_HOST = os.environ.get("PURESERVICE_HOST", "")

if not API_KEY:
    print("Set PURESERVICE_API_KEY first")
    sys.exit(1)

# Hosts to try, in order
HOSTS_TO_TRY = []
if EXPLICIT_HOST:
    HOSTS_TO_TRY.append(EXPLICIT_HOST)
HOSTS_TO_TRY += [
    "vanylven.pureservice.com",
    "vanylvenkommune.pureservice.com",
    "vanylven-kommune.pureservice.com",
    "kundenavn.pureservice.com",  # placeholder check
]

# Paths to try
PATHS_TO_TRY = [
    "/api/status/",
    "/api/v1/status/",
    "/agent/api/status/",
    "/api/ticket/",
]

# Auth header variants to try
AUTH_HEADERS_TO_TRY = [
    {"X-Authorization-Key": API_KEY},
    {"Authorization": f"Bearer {API_KEY}"},
    {"X-Authorization-Key": API_KEY, "Authorization": f"Bearer {API_KEY}"},
]


def check(host: str, path: str, auth: dict[str, str]) -> tuple[int, str, int]:
    """Return (status_code, short_body, body_length)."""
    headers = {
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        **auth,
    }
    url = f"https://{host}{path}"
    try:
        r = httpx.get(url, headers=headers, timeout=10, follow_redirects=False)
        body = r.text[:120].replace("\n", " ").replace("\r", "")
        return r.status_code, body, len(r.content)
    except httpx.ConnectError:
        return -1, "DNS / connect error", 0
    except Exception as e:
        return -2, f"{type(e).__name__}: {e}", 0


def status_marker(code: int) -> str:
    if code == 200:
        return "OK   "
    if code in (401, 403):
        return "AUTH "
    if code == 404:
        return "404  "
    if code in (301, 302, 307, 308):
        return "REDIR"
    if code < 0:
        return "ERR  "
    return f"{code} "


def main() -> None:
    print(f"API key: {'*' * 8}{API_KEY[-4:]}")
    print()

    # Step 1: which hosts even resolve?
    print("=" * 78)
    print("STEP 1: Which hosts respond at all?")
    print("=" * 78)
    reachable_hosts = []
    for host in HOSTS_TO_TRY:
        try:
            r = httpx.get(f"https://{host}/", timeout=8, follow_redirects=False)
            print(f"  [{r.status_code}] https://{host}/")
            if r.status_code < 500:
                reachable_hosts.append(host)
        except httpx.ConnectError:
            print(f"  [DNS] https://{host}/   (does not exist)")
        except Exception as e:
            print(f"  [ERR] https://{host}/   {type(e).__name__}")

    if not reachable_hosts:
        print("\nNo hosts reachable. Check the actual URL of your Pureservice instance.")
        print("Hint: log in via browser and copy the host from the address bar.")
        return

    # Step 2: try API paths against reachable hosts
    print()
    print("=" * 78)
    print("STEP 2: Trying API paths and auth combinations")
    print("=" * 78)
    print(f"{'STATUS':6} {'HOST':40} {'PATH':22} AUTH")
    print("-" * 78)

    successes = []
    auth_failures = []

    for host in reachable_hosts:
        for path in PATHS_TO_TRY:
            for i, auth in enumerate(AUTH_HEADERS_TO_TRY):
                auth_label = list(auth.keys())[0] if len(auth) == 1 else "both"
                code, body, _ = check(host, path, auth)
                marker = status_marker(code)
                print(f"{marker:6} {host:40} {path:22} {auth_label}")
                if code == 200:
                    successes.append((host, path, auth_label, body))
                elif code in (401, 403):
                    auth_failures.append((host, path, auth_label, body))

    # Step 3: summary
    print()
    print("=" * 78)
    print("RESULT")
    print("=" * 78)
    if successes:
        print(f"Found {len(successes)} working combination(s):")
        for host, path, auth_label, body in successes:
            print(f"  https://{host}{path}  via {auth_label}")
            print(f"    body preview: {body}")
        print()
        host, path, auth_label, _ = successes[0]
        print("Update test_pureservice_local.py:")
        print(f"  TENANT     = '{host.replace('.pureservice.com', '')}'")
        print(f"  base path  = '{path.rstrip('/').rsplit('/', 1)[0]}'")
        print(f"  auth       = '{auth_label}'")
    elif auth_failures:
        print("Endpoint found, but authentication failed.")
        print("This means the URL is right but the API key is wrong/expired/wrong-scope.")
        for host, path, auth_label, body in auth_failures[:3]:
            print(f"  https://{host}{path}  via {auth_label}")
            print(f"    -> {body}")
        print()
        print("Action: regenerate the API key in Pureservice admin and try again.")
    else:
        print("No combination worked.")
        print("Likely the host or path prefix is different from the standard.")
        print("Open Pureservice in your browser and look at the URL - that's the host.")


if __name__ == "__main__":
    main()
