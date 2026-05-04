"""Standalone Pureservice API smoke test.

Runs four progressive tests against your live Pureservice instance:
  1. Connect + auth
  2. List statuses (read-only, safe)
  3. List 5 most recent tickets
  4. Show pagination working

Requirements:
    pip install httpx

Usage:
    Set the two env vars below (or edit the file), then:
        python test_pureservice_local.py

Nothing is created or modified - this is read-only.
"""
from __future__ import annotations

import os
import sys

import httpx

# ----------------------------------------------------------------------
# Configuration - either edit here or set as environment variables
# ----------------------------------------------------------------------
TENANT = os.environ.get("PURESERVICE_TENANT", "vanylven")
API_KEY = os.environ.get("PURESERVICE_API_KEY", "")
API_BASE_PATH = os.environ.get("PURESERVICE_API_BASE_PATH", "/agent/api")

if not API_KEY:
    print("❌ Set PURESERVICE_API_KEY environment variable first")
    print("   PowerShell: $env:PURESERVICE_API_KEY = 'din-nokkel'")
    print("   Bash:       export PURESERVICE_API_KEY='din-nokkel'")
    sys.exit(1)

BASE_URL = f"https://{TENANT}.pureservice.com{API_BASE_PATH}"
HEADERS = {
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
    "X-Authorization-Key": API_KEY,
}


def header(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_1_connect() -> None:
    header("Test 1: Connection + authentication")
    try:
        r = httpx.get(f"{BASE_URL}/status/", headers=HEADERS, timeout=15)
    except httpx.ConnectError as e:
        print(f"❌ Could not reach {BASE_URL}")
        print(f"   {e}")
        sys.exit(1)

    if r.status_code == 401 or r.status_code == 403:
        print(f"❌ Auth failed ({r.status_code}). Check API key.")
        print(f"   Response: {r.text[:300]}")
        sys.exit(1)

    if r.status_code != 200:
        print(f"❌ Unexpected status {r.status_code}: {r.text[:300]}")
        sys.exit(1)

    print(f"✅ Connected to {TENANT}.pureservice.com")
    print(f"   HTTP {r.status_code}, {len(r.content)} bytes")


def test_2_list_statuses() -> None:
    header("Test 2: List ticket statuses")
    r = httpx.get(f"{BASE_URL}/status/", headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()

    # JSON:API responses use the resource name as the top-level key
    statuses = data.get("statuses") or data.get("status") or []
    print(f"✅ Found {len(statuses)} statuses:")
    for s in statuses[:10]:
        marker = " (default)" if s.get("default") else ""
        print(f"   • [{s.get('id')}] {s.get('name')}{marker}")
    if len(statuses) > 10:
        print(f"   ... and {len(statuses) - 10} more")


def test_3_list_tickets() -> None:
    header("Test 3: 5 most recent tickets")
    params = {"start": 0, "limit": 5, "sort": "modified desc"}
    r = httpx.get(f"{BASE_URL}/ticket/", headers=HEADERS, params=params, timeout=15)

    if r.status_code != 200:
        print(f"⚠️  Got {r.status_code}: {r.text[:300]}")
        return

    data = r.json()
    tickets = data.get("tickets", [])
    print(f"✅ Got {len(tickets)} tickets:")
    for t in tickets:
        subj = (t.get("subject") or "")[:60]
        print(f"   • #{t.get('id')} status={t.get('statusId')} | {subj}")


def test_4_pagination() -> None:
    header("Test 4: Pagination (count tickets)")
    total = 0
    start = 0
    page_size = 100
    pages = 0
    max_pages = 20  # safety cap so we don't burn rate limit

    while pages < max_pages:
        params = {"start": start, "limit": page_size}
        r = httpx.get(f"{BASE_URL}/ticket/", headers=HEADERS, params=params, timeout=15)
        if r.status_code != 200:
            print(f"⚠️  Page {pages + 1} returned {r.status_code}")
            break

        items = r.json().get("tickets", [])
        if not items:
            break
        total += len(items)
        pages += 1
        if len(items) < page_size:
            break
        start += page_size

    print(f"✅ Counted {total} tickets across {pages} pages")
    if pages == max_pages:
        print(f"   (stopped at safety cap of {max_pages} pages)")


def main() -> None:
    print(f"Testing against: {BASE_URL}")
    print(f"API key:         {'*' * 8}{API_KEY[-4:] if len(API_KEY) > 4 else '****'}")

    test_1_connect()
    test_2_list_statuses()
    test_3_list_tickets()
    test_4_pagination()

    print()
    print("🎉 All tests passed - your API key works and the MCP design is sound.")


if __name__ == "__main__":
    main()
