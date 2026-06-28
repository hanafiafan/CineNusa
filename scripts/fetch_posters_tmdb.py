# -*- coding: utf-8 -*-
"""
CineNusa — TMDB Poster Fetcher
================================
Ambil URL poster untuk setiap film dari TMDB API (gratis).

Cara pakai:
  1. Daftar di https://www.themoviedb.org/settings/api (gratis, instan)
  2. Copy API Key (v3 auth)
  3. Jalankan:
       set TMDB_API_KEY=your_key_here        (Windows CMD)
       $env:TMDB_API_KEY="your_key_here"     (PowerShell)
       python scripts/fetch_posters_tmdb.py

Output: CSV diperbarui dengan kolom poster_url yang terisi.
Progress disimpan di data/poster_cache.json sehingga bisa dilanjutkan.
"""
import os, sys, json, time, re
from pathlib import Path

# ── Dependencies check ────────────────────────────────────────────────────────
try:
    import requests
    import pandas as pd
    from tqdm import tqdm
except ImportError:
    print("Install deps dulu:  pip install requests pandas tqdm")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "poster_cache.json"

TMDB_KEY  = os.environ.get("TMDB_API_KEY", "").strip()
if not TMDB_KEY:
    TMDB_KEY = input("Masukkan TMDB API Key (v3): ").strip()
if not TMDB_KEY:
    print("API key diperlukan. Daftar di https://www.themoviedb.org/settings/api")
    sys.exit(1)

TMDB_SEARCH = "https://api.themoviedb.org/3/search/movie"
IMG_BASE    = "https://image.tmdb.org/t/p/w500"
DELAY       = 0.05   # ~15 req/s — masih jauh di bawah limit 40 req/10s


def find_csv() -> Path:
    for f in DATA_DIR.glob("*.csv"):
        return f
    raise FileNotFoundError(f"Tidak ada file CSV di {DATA_DIR}")


def clean_year(raw) -> int | None:
    if not raw or str(raw) in ("nan", "None", ""):
        return None
    m = re.search(r"(\d{4})", str(raw))
    return int(m.group(1)) if m else None


def search_tmdb(title: str, year: int | None = None) -> str | None:
    """Return full poster URL or None."""
    params = {
        "api_key":  TMDB_KEY,
        "query":    title,
        "language": "id",
        "region":   "ID",
        "include_adult": False,
    }
    if year:
        params["primary_release_year"] = year

    for attempt in (1, 2):
        try:
            r = requests.get(TMDB_SEARCH, params=params, timeout=10)
            r.raise_for_status()
            results = r.json().get("results", [])
            if results and results[0].get("poster_path"):
                return IMG_BASE + results[0]["poster_path"]
            # Second attempt: drop year constraint
            if attempt == 1 and year:
                params.pop("primary_release_year", None)
                continue
            return None
        except requests.RequestException as e:
            print(f"\n  [WARN] TMDB error untuk '{title}': {e}")
            return None
    return None


def main():
    csv_path = find_csv()
    print(f"Dataset : {csv_path.name}")

    df = pd.read_csv(csv_path)

    # Ensure poster_url column exists
    if "poster_url" not in df.columns:
        df["poster_url"] = ""

    # Load cache
    cache: dict = {}
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    fetched = filled_before = 0
    skipped = 0

    rows_todo = [
        (i, row) for i, row in df.iterrows()
        if not (str(row.get("poster_url", "")) not in ("", "nan", "None", "NaN")
                and str(row.get("poster_url", "")).startswith("http"))
    ]

    already_filled = len(df) - len(rows_todo)
    print(f"Sudah ada poster : {already_filled}")
    print(f"Perlu di-fetch   : {len(rows_todo)}")

    for i, row in tqdm(rows_todo, desc="Fetching posters", unit="film"):
        title = str(row.get("title", "")).strip()
        year  = clean_year(row.get("year"))
        key   = f"{title}|{year}"

        if key in cache:
            url = cache[key]
            skipped += 1
        else:
            url = search_tmdb(title, year)
            cache[key] = url or ""
            fetched += 1
            time.sleep(DELAY)

        if url:
            df.at[i, "poster_url"] = url
            filled_before += 1

    # Save cache
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save updated CSV
    df.to_csv(csv_path, index=False, encoding="utf-8")

    total_with_poster = df["poster_url"].apply(
        lambda x: bool(x and str(x) not in ("", "nan", "None", "NaN") and str(x).startswith("http"))
    ).sum()

    print(f"\n Selesai!")
    print(f"  Dari API  : {fetched} film")
    print(f"  Dari cache: {skipped} film")
    print(f"  Total poster: {total_with_poster} / {len(df)} film ({100*total_with_poster//len(df)}%)")
    print(f"  CSV diperbarui: {csv_path}")
    print(f"  Cache disimpan: {CACHE_FILE}")


if __name__ == "__main__":
    main()
