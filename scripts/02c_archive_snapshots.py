#!/usr/bin/env python3
"""
Archive snapshots builder: ensures Wayback Machine snapshots for corpus URLs.

For each URL in manifest.csv:
  1. Check if existing snapshot exists via availability API
  2. Create a fresh snapshot with Save Page Now (respecting rate limits)
  3. Re-query availability API to get final snapshot URL
  4. Log results to data/raw/archive_urls.json
"""

import csv
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Configuration
MANIFEST_PATH = Path("/Users/fridaruh/Documents/Proyectos/Tafoya/data/manifest.csv")
OUTPUT_PATH = Path("/Users/fridaruh/Documents/Proyectos/Tafoya/data/raw/archive_urls.json")
WAYBACK_AVAILABILITY_API = "https://archive.org/wayback/available"
WAYBACK_SAVE_API = "https://web.archive.org/save"

# Rate limiting and retry configuration
SAVE_REQUEST_INTERVAL_SECONDS = 15  # Max 1 save request every 15 seconds
SAVE_TIMEOUT_SECONDS = 120  # Timeout per save request
SAVE_MAX_RETRIES = 2  # Retry failed save requests up to 2 times
RETRY_BACKOFF_BASE = 2  # Exponential backoff: 2^retry seconds

# Session for connection pooling
session = requests.Session()
session.headers.update({
    "User-Agent": "Archive-Snapshot-Bot/1.0 (+https://github.com/fridaruh/tafoya)"
})

last_save_request_time = 0  # Track last save request for rate limiting


def get_existing_snapshot(url: str) -> Optional[Dict[str, str]]:
    """
    Query Wayback Machine availability API to check for existing snapshots.
    Returns: {"url": "...", "timestamp": "..."} or None if no snapshot exists.
    """
    try:
        response = session.get(
            WAYBACK_AVAILABILITY_API,
            params={"url": url},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get("archived_snapshots"):
            closest = data["archived_snapshots"].get("closest")
            if closest and closest.get("available"):
                timestamp = closest.get("timestamp", "")
                snapshot_url = f"https://web.archive.org/web/{timestamp}/{url}"
                return {
                    "url": snapshot_url,
                    "timestamp": timestamp
                }
        return None
    except Exception as e:
        print(f"  [ERROR] Failed to check availability for {url}: {e}")
        return None


def create_fresh_snapshot(url: str, existing_timestamp: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Create a fresh snapshot using Save Page Now API.
    Respects rate limiting, timeout, and retry logic.
    After save, re-queries availability API to get final snapshot URL.
    Returns: {"url": "...", "timestamp": "..."} or None if failed.
    """
    global last_save_request_time

    # Respect rate limit
    elapsed = time.time() - last_save_request_time
    if elapsed < SAVE_REQUEST_INTERVAL_SECONDS:
        sleep_time = SAVE_REQUEST_INTERVAL_SECONDS - elapsed
        print(f"  [RATE LIMIT] Waiting {sleep_time:.1f}s before save request...")
        time.sleep(sleep_time)

    # Retry loop with exponential backoff
    save_succeeded = False
    for attempt in range(SAVE_MAX_RETRIES + 1):
        try:
            last_save_request_time = time.time()

            print(f"  [SAVE] Attempt {attempt + 1}/{SAVE_MAX_RETRIES + 1} for {url}")
            response = session.get(
                WAYBACK_SAVE_API,
                params={"url": url},
                timeout=SAVE_TIMEOUT_SECONDS,
                allow_redirects=True
            )

            # Save Page Now returns 200/302 on success
            if response.status_code in [200, 302]:
                print(f"  [SAVE OK] Got status {response.status_code}, waiting for indexing...")
                save_succeeded = True
                break

            # Handle specific error codes
            if response.status_code in [429, 500, 502, 503, 504]:
                if attempt < SAVE_MAX_RETRIES:
                    backoff = RETRY_BACKOFF_BASE ** attempt
                    print(f"  [RETRY] Status {response.status_code}, retrying in {backoff}s...")
                    time.sleep(backoff)
                    continue
                else:
                    print(f"  [FAILED] Status {response.status_code} after {SAVE_MAX_RETRIES} retries")
                    return None

            # Other status codes
            print(f"  [FAILED] Status {response.status_code}")
            return None

        except requests.exceptions.Timeout:
            if attempt < SAVE_MAX_RETRIES:
                backoff = RETRY_BACKOFF_BASE ** attempt
                print(f"  [RETRY] Timeout, retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                print(f"  [FAILED] Timeout after {SAVE_MAX_RETRIES} retries")
                return None
        except Exception as e:
            if attempt < SAVE_MAX_RETRIES:
                backoff = RETRY_BACKOFF_BASE ** attempt
                print(f"  [RETRY] Error: {e}, retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                print(f"  [FAILED] Error: {e}")
                return None

    if not save_succeeded:
        return None

    # Wait for Wayback Machine to index the new snapshot
    print("  [WAIT] Waiting 10s for snapshot to be indexed...")
    time.sleep(10)

    # Re-query availability API to get the fresh snapshot
    print("  [VERIFY] Verifying fresh snapshot...")
    try:
        response = session.get(
            WAYBACK_AVAILABILITY_API,
            params={"url": url},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get("archived_snapshots"):
            closest = data["archived_snapshots"].get("closest")
            if closest and closest.get("available"):
                new_timestamp = closest.get("timestamp", "")
                # Only return if timestamp is different from existing
                if new_timestamp and new_timestamp != existing_timestamp:
                    snapshot_url = f"https://web.archive.org/web/{new_timestamp}/{url}"
                    print(f"  [VERIFIED] New snapshot at {new_timestamp}")
                    return {
                        "url": snapshot_url,
                        "timestamp": new_timestamp
                    }
                else:
                    print(f"  [SKIP] No new snapshot (same timestamp: {new_timestamp})")
                    return None
        return None
    except Exception as e:
        print(f"  [ERROR] Failed to verify fresh snapshot: {e}")
        return None




def process_urls():
    """
    Main processing loop: read URLs from manifest, archive each one.
    """
    results = {}

    # Read manifest.csv
    print("[INFO] Reading manifest.csv...")
    try:
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            urls_to_process = [(row['doc_id'], row['url']) for row in reader if row['url']]
    except Exception as e:
        print(f"[ERROR] Failed to read manifest.csv: {e}")
        return {}

    print(f"[INFO] Found {len(urls_to_process)} URLs to process")

    # Process each URL
    for idx, (doc_id, url) in enumerate(urls_to_process, 1):
        print(f"\n[{idx}/{len(urls_to_process)}] Processing {doc_id}")
        print(f"  URL: {url}")

        result = {
            "url": url,
            "existing_snapshot": None,
            "fresh_snapshot": None,
            "status": "ok",
            "error": None
        }

        try:
            # Step 1: Check for existing snapshot
            print("  [CHECK] Looking for existing snapshot...")
            existing = get_existing_snapshot(url)
            if existing:
                result["existing_snapshot"] = existing
                print(f"  [FOUND] Existing snapshot: {existing['timestamp']}")
            else:
                print("  [NOT FOUND] No existing snapshot")

            # Step 2: Create fresh snapshot
            print("  [CREATE] Creating fresh snapshot...")
            existing_ts = existing["timestamp"] if existing else None
            fresh = create_fresh_snapshot(url, existing_ts)
            if fresh:
                result["fresh_snapshot"] = fresh
                print(f"  [CREATED] Fresh snapshot: {fresh['timestamp']}")
            else:
                print("  [FAILED] Could not create fresh snapshot")

                # If fresh snapshot failed, mark as partial or failed
                if existing:
                    result["status"] = "partial"
                    result["error"] = "Fresh snapshot creation failed, but existing snapshot available"
                else:
                    result["status"] = "failed"
                    result["error"] = "Both fresh and existing snapshot unavailable"

            # Step 3: If fresh snapshot was created, verify it
            if fresh is None and existing is None:
                result["status"] = "failed"
                result["error"] = "No snapshot available"
            elif fresh is None and existing:
                result["status"] = "partial"
                result["error"] = "Only existing snapshot available"

        except Exception as e:
            print(f"  [ERROR] Unexpected error: {e}")
            if result["existing_snapshot"]:
                result["status"] = "partial"
                result["error"] = f"Processing error: {str(e)}, but existing snapshot available"
            else:
                result["status"] = "failed"
                result["error"] = f"Processing error: {str(e)}"

        results[doc_id] = result

        # Brief pause between documents
        if idx < len(urls_to_process):
            time.sleep(1)

    return results


def main():
    """
    Main entry point.
    """
    print("=" * 70)
    print("Archive Snapshots Builder")
    print("=" * 70)
    print(f"Start time: {datetime.now().isoformat()}")

    start_time = time.time()

    # Process all URLs
    results = process_urls()

    # Save results
    print(f"\n[INFO] Saving results to {OUTPUT_PATH}")
    try:
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print("[SUCCESS] Results saved")
    except Exception as e:
        print(f"[ERROR] Failed to save results: {e}")
        return 1

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    ok_count = sum(1 for r in results.values() if r["status"] == "ok")
    partial_count = sum(1 for r in results.values() if r["status"] == "partial")
    failed_count = sum(1 for r in results.values() if r["status"] == "failed")

    print(f"OK:      {ok_count}")
    print(f"Partial: {partial_count}")
    print(f"Failed:  {failed_count}")
    print(f"Total:   {len(results)}")

    # List failed docs
    if failed_count > 0:
        print(f"\nDocs without any snapshot ({failed_count}):")
        for doc_id, result in results.items():
            if result["status"] == "failed":
                print(f"  - {doc_id}")

    elapsed = time.time() - start_time
    print(f"\nEnd time: {datetime.now().isoformat()}")
    print(f"Elapsed time: {elapsed:.1f}s")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
