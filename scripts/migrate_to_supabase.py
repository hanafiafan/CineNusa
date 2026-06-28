# -*- coding: utf-8 -*-
"""
CineNusa — Migrate CSV → Supabase
====================================
Baca dataset CSV dan upload ke tabel movies di Supabase.

Cara pakai:
  1. Set env vars SUPABASE_URL dan SUPABASE_ANON_KEY
  2. Jalankan:
       python scripts/migrate_to_supabase.py

  Atau dengan service key untuk bypass RLS:
       set SUPABASE_KEY=<service_role_key>
       python scripts/migrate_to_supabase.py
"""
import os, sys, re, math
from pathlib import Path

try:
    import pandas as pd
    from tqdm import tqdm
except ImportError:
    print("pip install pandas tqdm")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

try:
    from supabase import create_client
except ImportError:
    print("pip install supabase")
    sys.exit(1)


def get_service_client():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_KEY") or
           os.environ.get("SUPABASE_ANON_KEY", "")).strip()
    if not url or not key:
        print("Set SUPABASE_URL dan SUPABASE_SERVICE_KEY di .env")
        sys.exit(1)
    return create_client(url, key)


def upsert_chunk(sb, records):
    sb.table("movies").upsert(records, on_conflict="movie_id").execute()


def clean_val(v):
    if v is None:
        return None
    s = str(v).strip()
    if s in ("nan", "None", "NaN", ""):
        return None
    return s


def clean_int(v):
    try:
        f = float(v)
        return None if math.isnan(f) else int(f)
    except (TypeError, ValueError):
        return None


def clean_float(v):
    try:
        f = float(v)
        return None if math.isnan(f) else round(f, 2)
    except (TypeError, ValueError):
        return None


def find_csv() -> Path:
    data_dir = BASE_DIR / "data"
    for f in data_dir.glob("*.csv"):
        return f
    raise FileNotFoundError(f"No CSV found in {data_dir}")


def main():
    sb = get_service_client()

    csv_path = find_csv()
    print(f"Membaca: {csv_path.name}")
    df = pd.read_csv(csv_path)
    print(f"Total film: {len(df)}")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    COL = {
        "movie_id":   next((c for c in df.columns if "id" in c and "movie" in c), None) or "movieid",
        "title":      next((c for c in df.columns if "title" in c), "title"),
        "year":       next((c for c in df.columns if "year" in c), None),
        "genre":      next((c for c in df.columns if "genre" in c), None),
        "director":   next((c for c in df.columns if "director" in c), None),
        "stars":      next((c for c in df.columns if "star" in c or "cast" in c), None),
        "description":next((c for c in df.columns if "desc" in c or "plot" in c or "synop" in c), None),
        "rating":     next((c for c in df.columns if "rating" in c or "imdb" in c), None),
        "votes":      next((c for c in df.columns if "vote" in c), None),
        "duration":   next((c for c in df.columns if "dur" in c or "runtime" in c or "time" in c), None),
        "poster_url": next((c for c in df.columns if "poster" in c or "image" in c or "url" in c), None),
    }
    print("Kolom mapping:", {k: v for k, v in COL.items() if v})

    records = []
    for idx, row in df.iterrows():
        movie_id = clean_int(row.get(COL["movie_id"], idx + 1)) or (idx + 1)
        title    = clean_val(row.get(COL["title"], ""))
        if not title:
            continue

        rec = {
            "movie_id":    movie_id,
            "title":       title,
            "year":        clean_int(row.get(COL["year"])) if COL["year"] else None,
            "genre":       clean_val(row.get(COL["genre"])) if COL["genre"] else None,
            "director":    clean_val(row.get(COL["director"])) if COL["director"] else None,
            "stars":       clean_val(row.get(COL["stars"])) if COL["stars"] else None,
            "description": clean_val(row.get(COL["description"])) if COL["description"] else None,
            "rating":      clean_float(row.get(COL["rating"])) if COL["rating"] else None,
            "votes":       clean_int(row.get(COL["votes"])) if COL["votes"] else None,
            "duration":    clean_val(row.get(COL["duration"])) if COL["duration"] else None,
            "poster_url":  clean_val(row.get(COL["poster_url"])) if COL["poster_url"] else None,
        }
        records.append(rec)

    print(f"Mengupload {len(records)} film ke Supabase...")
    chunk = 200
    for i in tqdm(range(0, len(records), chunk), desc="Uploading", unit="batch"):
        upsert_chunk(sb, records[i:i+chunk])

    print(f"\nSelesai! {len(records)} film tersimpan di Supabase.")
    print("Jalankan server: python app.py")


if __name__ == "__main__":
    main()
