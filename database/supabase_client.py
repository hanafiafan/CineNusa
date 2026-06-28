# -*- coding: utf-8 -*-
"""
CineNusa — Supabase Client
Provides a lazy singleton for the Supabase Python client.
Falls back gracefully if env vars are missing (CSV mode).
"""
import os
from functools import lru_cache
from typing import Optional

try:
    from supabase import create_client, Client
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False
    Client = None  # type: ignore


@lru_cache(maxsize=1)
def get_client() -> Optional["Client"]:
    """Return a cached Supabase client or None if not configured."""
    if not _SUPABASE_AVAILABLE:
        return None
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        return None
    return create_client(url, key)


def is_available() -> bool:
    return get_client() is not None


# ── Movies ────────────────────────────────────────────────────────────────────

def fetch_all_movies() -> list[dict]:
    """Load all movies from Supabase (paginated)."""
    sb = get_client()
    if not sb:
        return []
    results, page_size, offset = [], 1000, 0
    while True:
        resp = (sb.table("movies")
                  .select("*")
                  .range(offset, offset + page_size - 1)
                  .execute())
        batch = resp.data or []
        results.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return results


def upsert_movies(records: list[dict]) -> None:
    """Bulk upsert movies (used by migration script)."""
    sb = get_client()
    if not sb or not records:
        return
    chunk = 500
    for i in range(0, len(records), chunk):
        sb.table("movies").upsert(records[i:i+chunk],
                                  on_conflict="movie_id").execute()


def search_movies_db(query: str, field: str = "all", limit: int = 20) -> list[dict]:
    """Full-text or field search via Supabase."""
    sb = get_client()
    if not sb:
        return []
    q = sb.table("movies").select("*").limit(limit)
    if field == "title":
        q = q.ilike("title", f"%{query}%")
    elif field == "genre":
        q = q.ilike("genre", f"%{query}%")
    elif field == "director":
        q = q.ilike("director", f"%{query}%")
    else:
        # text search across title + genre + director
        q = q.or_(f"title.ilike.%{query}%,genre.ilike.%{query}%,director.ilike.%{query}%")
    return q.execute().data or []


# ── Ratings ───────────────────────────────────────────────────────────────────

def get_session_ratings(session_id: str) -> dict[int, float]:
    """Return {movie_id: rating} for a session."""
    sb = get_client()
    if not sb or not session_id:
        return {}
    rows = (sb.table("user_ratings")
              .select("movie_id, rating")
              .eq("session_id", session_id)
              .execute().data or [])
    return {r["movie_id"]: float(r["rating"]) for r in rows}


def upsert_rating(session_id: str, movie_id: int, rating: float) -> None:
    sb = get_client()
    if not sb:
        return
    sb.table("user_ratings").upsert(
        {"session_id": session_id, "movie_id": movie_id, "rating": rating},
        on_conflict="session_id,movie_id"
    ).execute()


def delete_rating(session_id: str, movie_id: int) -> None:
    sb = get_client()
    if not sb:
        return
    sb.table("user_ratings").delete().eq("session_id", session_id).eq("movie_id", movie_id).execute()


def clear_session_ratings(session_id: str) -> None:
    sb = get_client()
    if not sb:
        return
    sb.table("user_ratings").delete().eq("session_id", session_id).execute()
