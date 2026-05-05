#!/usr/bin/env python3
"""
Download offline JS assets for the Enterprise Dashboard.

Run ONCE on a machine with internet access, then transfer the
bundled static folder to the offline server.

Usage:
    python download_assets.py
"""

import urllib.request
import pathlib
import sys

ASSETS = [
    # (URL, local relative path)
    (
        'https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js',
        'app/static/js/chart.min.js',
    ),
    (
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
        'app/static/css/bootstrap.min.css',
    ),
    (
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
        'app/static/js/bootstrap.bundle.min.js',
    ),
    (
        'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
        'app/static/css/bootstrap-icons.css',
    ),
    (
        'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2',
        'app/static/css/fonts/bootstrap-icons.woff2',
    ),
]

def download(url: str, dest: str) -> None:
    path = pathlib.Path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        print(f'  ✓ Already exists: {dest}')
        return
    print(f'  ↓ Downloading {dest} …', end=' ', flush=True)
    try:
        urllib.request.urlretrieve(url, path)
        size = path.stat().st_size
        print(f'OK ({size:,} bytes)')
    except Exception as e:
        print(f'FAILED: {e}')
        sys.exit(1)

if __name__ == '__main__':
    print('\n📦 Enterprise Dashboard — Offline Asset Downloader')
    print('=' * 52)
    for url, dest in ASSETS:
        download(url, dest)
    print('\n✅ All assets downloaded. You can now run: python run.py\n')
