# -*- coding: utf-8 -*-
"""
CineNusa — Sistem Rekomendasi Film Indonesia
Flask web application  |  Hybrid SVD + Content-Based Filtering
Run: python app.py
"""
import os

# Load .env in development (no-op in production if file absent)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import (Flask, render_template, request, session,
                   redirect, url_for, jsonify, flash)
from recommender import IndonesianMovieRecommender

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'cinenusa-svd-2026-senatib-fallback')

# ── Supabase ratings helper ───────────────────────────────────────────────────
try:
    from database import supabase_client as _sb
    _USE_SUPABASE = _sb.is_available()
except Exception:
    _USE_SUPABASE = False

def _sid() -> str:
    """Stable session identifier."""
    if 'sid' not in session:
        import uuid
        session['sid'] = str(uuid.uuid4())
    return session['sid']

def _get_ratings() -> dict:
    if _USE_SUPABASE:
        return _sb.get_session_ratings(_sid())
    return {int(k): float(v) for k, v in session.get('ratings', {}).items()}

def _save_rating(movie_id: int, rating: float):
    if _USE_SUPABASE:
        _sb.upsert_rating(_sid(), movie_id, rating)
    else:
        r = dict(session.get('ratings', {}))
        r[str(movie_id)] = rating
        session['ratings'] = r
        session.modified = True

def _delete_rating(movie_id: int):
    if _USE_SUPABASE:
        _sb.delete_rating(_sid(), movie_id)
    else:
        r = dict(session.get('ratings', {}))
        r.pop(str(movie_id), None)
        session['ratings'] = r
        session.modified = True

def _clear_ratings():
    if _USE_SUPABASE:
        _sb.clear_session_ratings(_sid())
    else:
        session.pop('ratings', None)

# ── Initialize recommender ────────────────────────────────────────────────────
rec = IndonesianMovieRecommender()
READY = False

try:
    rec.initialize()
    READY = True
except FileNotFoundError as e:
    print(f"\n{'='*60}")
    print(str(e))
    print('='*60)
except Exception as e:
    print(f"Init error: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _df_to_list(df):
    return df.to_dict('records') if df is not None and len(df) else []


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if not READY:
        return render_template('setup.html')

    featured   = _df_to_list(rec.get_top_rated(18))
    genres     = rec.get_genres()
    n_rated    = len(_get_ratings())
    dataset_stats = rec.stats() if READY else {}

    return render_template('index.html',
                           featured=featured,
                           genres=genres,
                           n_rated=n_rated,
                           stats=dataset_stats)


@app.route('/search')
def search():
    query  = request.args.get('q', '').strip()
    field  = request.args.get('field', 'all')
    genre  = request.args.get('genre', '').strip()

    results = []
    if query:
        results = _df_to_list(rec.search(query, field))
    elif genre:
        results = _df_to_list(rec.search(genre, 'genre'))

    return render_template('search.html',
                           results=results,
                           query=query,
                           genre=genre,
                           field=field,
                           genres=rec.get_genres(),
                           n_rated=len(_get_ratings()))


@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    movie = rec.get_by_id(movie_id)
    if movie is None:
        flash('Film tidak ditemukan.', 'warning')
        return redirect(url_for('index'))

    similar       = _df_to_list(rec.get_similar_movies(movie['title'], n=6))
    user_ratings  = _get_ratings()
    user_rating   = user_ratings.get(movie_id)

    return render_template('movie.html',
                           movie=movie,
                           similar=similar,
                           user_rating=user_rating,
                           n_rated=len(user_ratings))


@app.route('/rate', methods=['POST'])
def rate():
    movie_id = request.form.get('movie_id', type=int)
    rating   = request.form.get('rating', type=float)
    action   = request.form.get('action', 'rate')   # 'rate' or 'delete'

    if movie_id is None:
        return redirect(url_for('index'))

    if action == 'delete':
        _delete_rating(movie_id)
        flash('Rating dihapus.', 'info')
    elif rating is not None and 0.5 <= rating <= 5.0:
        _save_rating(movie_id, rating)
        flash(f'Rating {rating} bintang tersimpan!', 'success')
    else:
        flash('Rating tidak valid (0.5 – 5.0).', 'danger')

    return redirect(url_for('movie_detail', movie_id=movie_id))


@app.route('/recommendations')
def recommendations():
    user_ratings = _get_ratings()

    if not user_ratings:
        flash('Rating minimal 1 film dulu untuk mendapat rekomendasi personal.', 'info')
        return redirect(url_for('index'))

    recs = _df_to_list(rec.get_personalized_recommendations(user_ratings, n=12))

    rated = []
    for mid, rating in sorted(user_ratings.items(), key=lambda x: x[1], reverse=True):
        m = rec.get_by_id(mid)
        if m:
            m['user_rating'] = rating
            rated.append(m)

    return render_template('recommendations.html',
                           recs=recs,
                           rated=rated,
                           n_rated=len(user_ratings))


@app.route('/swipe')
def swipe():
    movies = _df_to_list(rec.get_top_rated(60))
    import random; random.shuffle(movies)
    return render_template('swipe.html', movies=movies[:40],
                           n_rated=len(_get_ratings()))

@app.route('/compare')
def compare():
    id1 = request.args.get('id1', type=int)
    id2 = request.args.get('id2', type=int)
    m1  = rec.get_by_id(id1) if id1 else None
    m2  = rec.get_by_id(id2) if id2 else None
    top = _df_to_list(rec.get_top_rated(200))
    return render_template('compare.html', m1=m1, m2=m2, top=top,
                           n_rated=len(_get_ratings()))

@app.route('/genre/<genre_name>')
def genre_page(genre_name):
    results = _df_to_list(rec.search(genre_name, 'genre', n=50))
    return render_template('search.html',
                           results=results,
                           query='',
                           genre=genre_name,
                           field='genre',
                           genres=rec.get_genres(),
                           n_rated=len(_get_ratings()))


@app.route('/clear-ratings')
def clear_ratings():
    _clear_ratings()
    flash('Semua rating telah dihapus.', 'info')
    return redirect(url_for('index'))


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route('/api/search')
def api_search():
    q     = request.args.get('q', '')
    field = request.args.get('field', 'all')
    n     = request.args.get('n', 16, type=int)
    results = _df_to_list(rec.search(q, field, n)) if q else []
    return jsonify(results)


@app.route('/api/movie/<int:movie_id>')
def api_movie(movie_id):
    m = rec.get_by_id(movie_id)
    return jsonify(m or {})


@app.route('/api/stats')
def api_stats():
    return jsonify(rec.stats() if READY else {})


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n  CineNusa — Sistem Rekomendasi Film Indonesia")
    print("  Buka browser: http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000, use_reloader=False)
