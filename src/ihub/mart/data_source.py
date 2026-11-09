"""Obtain the DuckDB file the app reads, at runtime.

Streamlit Community Cloud does not bake data into an image, so when no local
file is present the app downloads the newest published ``data-*`` GitHub
Release asset ``ihub.duckdb``. The repository is public, so no token is needed.
Local development uses the file at ``IHUB_DUCKDB_PATH`` if it already exists.
See docs/DEPLOYMENT.md.
"""

from __future__ import annotations

from pathlib import Path

import httpx

REPO = "DataLab-UNZA/ihub-data-analytics-platform"
_RELEASES_URL = f"https://api.github.com/repos/{REPO}/releases"
_ASSET_NAME = "ihub.duckdb"


def latest_data_asset() -> tuple[str, str] | None:
    """Return ``(tag, download_url)`` for the newest ``data-*`` release, or None."""
    try:
        resp = httpx.get(
            _RELEASES_URL,
            params={"per_page": 100},
            headers={"Accept": "application/vnd.github+json"},
            timeout=15.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        return None
    releases = [r for r in resp.json() if str(r.get("tag_name", "")).startswith("data-")]
    releases.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    for release in releases:
        for asset in release.get("assets", []):
            if asset.get("name") == _ASSET_NAME:
                return release["tag_name"], asset["browser_download_url"]
    return None


def ensure_duckdb(local_path: Path, cache_dir: Path | None = None) -> Path | None:
    """Return a usable DuckDB path, downloading the newest release if needed.

    If ``local_path`` already exists (local development), it is used as-is.
    Otherwise the newest ``data-*`` release asset is downloaded into
    ``cache_dir`` (default: the parent of ``local_path``) and that path is
    returned. Returns None when no data has been published yet or the download
    fails.
    """
    if local_path.exists():
        return local_path
    latest = latest_data_asset()
    if latest is None:
        return None
    tag, url = latest
    cache_dir = cache_dir or local_path.parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"ihub-{tag}.duckdb"
    if target.exists():
        return target
    partial = cache_dir / f"{target.name}.part"
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as resp:
            resp.raise_for_status()
            with partial.open("wb") as handle:
                for chunk in resp.iter_bytes():
                    handle.write(chunk)
    except httpx.HTTPError:
        partial.unlink(missing_ok=True)
        return None
    partial.replace(target)
    return target
