-- ══════════════════════════════════════════════════════════════════════════
-- CineNusa — Supabase Schema
-- Jalankan di Supabase SQL Editor: https://supabase.com/dashboard
-- ══════════════════════════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Movies ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS movies (
  id          BIGSERIAL PRIMARY KEY,
  movie_id    INTEGER   UNIQUE NOT NULL,
  title       TEXT      NOT NULL,
  year        INTEGER,
  genre       TEXT,
  director    TEXT,
  stars       TEXT,
  description TEXT,
  rating      NUMERIC(4,2),
  votes       BIGINT,
  duration    TEXT,
  poster_url  TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_movies_movie_id ON movies(movie_id);
CREATE INDEX IF NOT EXISTS idx_movies_genre    ON movies USING GIN (to_tsvector('simple', COALESCE(genre, '')));
CREATE INDEX IF NOT EXISTS idx_movies_title    ON movies USING GIN (to_tsvector('simple', title));
CREATE INDEX IF NOT EXISTS idx_movies_rating   ON movies(rating DESC NULLS LAST);

-- ── User Ratings ──────────────────────────────────────────────────────────────
-- Replaces Flask sessions — persistent across devices/sessions
CREATE TABLE IF NOT EXISTS user_ratings (
  id          BIGSERIAL PRIMARY KEY,
  session_id  TEXT      NOT NULL,
  movie_id    INTEGER   NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
  rating      NUMERIC(3,1) NOT NULL CHECK (rating BETWEEN 0.5 AND 5.0),
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (session_id, movie_id)
);

CREATE INDEX IF NOT EXISTS idx_ratings_session  ON user_ratings(session_id);
CREATE INDEX IF NOT EXISTS idx_ratings_movie_id ON user_ratings(movie_id);

-- ── Recommendation Cache ──────────────────────────────────────────────────────
-- Store pre-computed or cached recommendations keyed by session fingerprint
CREATE TABLE IF NOT EXISTS recommendation_cache (
  id          BIGSERIAL PRIMARY KEY,
  cache_key   TEXT      NOT NULL,        -- hash of user_ratings dict
  movie_id    INTEGER   NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
  score       NUMERIC(6,4),
  rank        INTEGER,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reccache_key ON recommendation_cache(cache_key);

-- Auto-expire cache after 24h (run via pg_cron or handle in app)
-- DELETE FROM recommendation_cache WHERE created_at < NOW() - INTERVAL '24 hours';

-- ── Trigger: updated_at ───────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_movies_updated_at
  BEFORE UPDATE ON movies
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_ratings_updated_at
  BEFORE UPDATE ON user_ratings
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Row Level Security (RLS) ──────────────────────────────────────────────────
-- Enable RLS — use anon key safely in frontend
ALTER TABLE movies           ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_ratings     ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendation_cache ENABLE ROW LEVEL SECURITY;

-- Anyone can read movies
CREATE POLICY "Public read movies"
  ON movies FOR SELECT USING (true);

-- Anyone can read/write their own ratings (by session_id — not user auth)
CREATE POLICY "Session read ratings"
  ON user_ratings FOR SELECT USING (true);

CREATE POLICY "Session insert ratings"
  ON user_ratings FOR INSERT WITH CHECK (true);

CREATE POLICY "Session update ratings"
  ON user_ratings FOR UPDATE USING (true);

CREATE POLICY "Session delete ratings"
  ON user_ratings FOR DELETE USING (true);

-- Recommendation cache — readable by all
CREATE POLICY "Public read reccache"
  ON recommendation_cache FOR SELECT USING (true);

CREATE POLICY "Public insert reccache"
  ON recommendation_cache FOR INSERT WITH CHECK (true);

-- ── Useful views ──────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW v_top_rated AS
  SELECT movie_id, title, year, genre, director, rating, votes, poster_url,
         (rating * LOG(GREATEST(votes, 1))) AS bayesian_score
  FROM   movies
  WHERE  rating IS NOT NULL AND votes > 10
  ORDER  BY bayesian_score DESC;
