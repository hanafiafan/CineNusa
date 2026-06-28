# -*- coding: utf-8 -*-
"""
CineNusa — IndonesianMovieRecommender
Hybrid engine: Content-Based Filtering (TF-IDF + Cosine)
+ SVD Collaborative Filtering (scipy — Vercel-compatible, no scikit-surprise)

Dataset: IMDB Indonesian Movies (Kaggle: dionisiusdh/imdb-indonesian-movies)
"""
import os, warnings
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
import joblib
warnings.filterwarnings('ignore')

# ── Column aliases ────────────────────────────────────────────────────────────
_COL_MAP = {
    'title':       ['title', 'judul', 'name', 'movie_title', 'film'],
    'year':        ['year', 'tahun', 'release_year', 'rilis'],
    'rating':      ['rating', 'imdb_rating', 'score', 'nilai'],
    'votes':       ['votes', 'num_votes', 'vote_count', 'jumlah_suara'],
    'genre':       ['genre', 'genres', 'kategori', 'jenis'],
    'director':    ['director', 'direktur', 'sutradara'],
    'stars':       ['stars', 'cast', 'actor', 'pemain', 'bintang'],
    'description': ['description', 'desc', 'synopsis', 'plot', 'sinopsis', 'overview'],
    'duration':    ['duration', 'runtime', 'durasi', 'menit'],
    'poster_url':  ['poster', 'poster_url', 'image', 'img_url'],
}

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ON_VERCEL = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))
# On Vercel /tmp is the only writable path; locally use models/
MODEL_PATH = (
    '/tmp/cinenusa_svd.pkl' if _ON_VERCEL
    else os.path.join(_BASE_DIR, 'models', 'svd_model.pkl')
)


class IndonesianMovieRecommender:

    def __init__(self, data_path=None):
        self.data_path    = data_path or os.path.join(_BASE_DIR, 'data', 'imdb_indonesian_movies.csv')
        self.df           = None
        self.cosine_sim   = None
        self.title_to_idx = {}
        self.movieid_to_dfidx = {}

        # SVD factors (scipy-based)
        self.svd_U        = None   # (n_users, k)
        self.svd_S        = None   # (k,)
        self.svd_Vt       = None   # (k, n_items)
        self.item_idx     = {}     # movieId → column index in SVD matrix
        self._global_mean = 2.5

    # ── Data loading ──────────────────────────────────────────────────────────

    def _find_csv(self):
        data_dir = os.path.dirname(self.data_path) or os.path.join(_BASE_DIR, 'data')
        if os.path.exists(self.data_path):
            return self.data_path
        if os.path.isdir(data_dir):
            for f in os.listdir(data_dir):
                if f.lower().endswith('.csv'):
                    return os.path.join(data_dir, f)
        return self.data_path

    def load_data(self):
        # Optional: try Supabase first
        try:
            from database.supabase_client import is_available, fetch_all_movies
            if is_available():
                records = fetch_all_movies()
                if records:
                    df = pd.DataFrame(records)
                    self._finalize_df(df)
                    print(f"  Loaded {len(self.df):,} movies from Supabase")
                    return self.df
        except Exception:
            pass

        # Fallback: CSV
        csv_path = self._find_csv()
        if not os.path.exists(csv_path):
            raise FileNotFoundError(
                f"Dataset tidak ditemukan di folder data/\n"
                "Download: kaggle datasets download dionisiusdh/imdb-indonesian-movies\n"
                "Extract CSV ke folder data/"
            )
        self.data_path = csv_path
        df = pd.read_csv(self.data_path, low_memory=False)

        # Flexible column rename
        rename = {}
        for std, aliases in _COL_MAP.items():
            for col in df.columns:
                if col.lower().strip() in aliases:
                    rename[col] = std
                    break
        df = df.rename(columns=rename)

        self._finalize_df(df)
        print(f"  Loaded {len(self.df):,} movies from CSV")
        return self.df

    def _finalize_df(self, df):
        defaults = {
            'title': '', 'year': '', 'rating': 6.0, 'votes': 100,
            'genre': 'Drama', 'director': '', 'stars': '',
            'description': '', 'duration': '', 'poster_url': ''
        }
        for col, default in defaults.items():
            if col not in df.columns:
                df[col] = default

        df['title']       = df['title'].fillna('').astype(str).str.strip()
        df['rating']      = pd.to_numeric(df['rating'], errors='coerce').fillna(6.0)
        df['votes']       = pd.to_numeric(df['votes'], errors='coerce').fillna(100)
        df['genre']       = df['genre'].fillna('').astype(str)
        df['director']    = df['director'].fillna('').astype(str)
        df['stars']       = df['stars'].fillna('').astype(str)
        df['description'] = df['description'].fillna('').astype(str)
        df['poster_url']  = df['poster_url'].fillna('').astype(str)
        df['year']        = df['year'].astype(str).str.extract(r'(\d{4})')[0].fillna('')

        # Normalise IMDB 1-10 rating → 1-5
        df['rating_norm'] = df['rating'].apply(lambda r: r / 2.0 if r > 5.5 else r)

        df = df[df['title'] != ''].drop_duplicates(subset=['title']).reset_index(drop=True)
        df['movieId'] = range(1, len(df) + 1)

        self.df = df
        self.title_to_idx     = {t: i for i, t in enumerate(df['title'])}
        self.movieid_to_dfidx = {int(row['movieId']): i for i, row in df.iterrows()}

    # ── Content model ─────────────────────────────────────────────────────────

    def build_content_model(self):
        def soup(row):
            g = row['genre'].replace(',', ' ').replace('|', ' ')
            d = row['director'].replace(',', ' ')
            s = row['stars'].replace(',', ' ')
            return f"{g} {g} {d} {s}"

        self.df['_soup'] = self.df.apply(soup, axis=1)
        tfidf = TfidfVectorizer(stop_words='english', max_features=8000, ngram_range=(1, 2))
        mat   = tfidf.fit_transform(self.df['_soup'])
        self.cosine_sim = cosine_similarity(mat, mat)
        print(f"  Content model: {mat.shape[0]} films × {mat.shape[1]} features")

    # ── SVD (scipy — Vercel compatible, no scikit-surprise) ───────────────────

    def generate_synthetic_ratings(self, n_users=400, seed=42):
        np.random.seed(seed)
        n_movies = len(self.df)

        all_genres = set()
        for g in self.df['genre']:
            for x in g.replace('|', ',').split(','):
                x = x.strip()
                if x:
                    all_genres.add(x)
        all_genres = list(all_genres) or ['Drama']

        rows = []
        for uid in range(1, n_users + 1):
            fav     = np.random.choice(all_genres, size=min(3, len(all_genres)), replace=False)
            n_rated = np.random.randint(15, min(71, n_movies))
            indices = np.random.choice(n_movies, n_rated, replace=False)

            for idx in indices:
                row   = self.df.iloc[idx]
                base  = row['rating_norm']
                boost = sum(0.3 for g in fav if g.lower() in row['genre'].lower())
                sigma = max(0.2, 1.0 / np.log1p(max(row['votes'], 1)))
                r = np.clip(np.random.normal(base + boost, sigma), 0.5, 5.0)
                r = round(r * 2) / 2
                rows.append({'userId': uid, 'movieId': int(row['movieId']), 'rating': r})

        self._syn_ratings = pd.DataFrame(rows)
        print(f"  Synthetic ratings: {len(rows):,} ({n_users} users)")
        return self._syn_ratings

    def train_svd(self, n_factors=50):
        """
        Truncated SVD via scipy.sparse.linalg.svds.
        Replaces scikit-surprise — fully compatible with Vercel Python runtime.
        """
        if not hasattr(self, '_syn_ratings'):
            self.generate_synthetic_ratings()

        ratings_df = self._syn_ratings

        # Build ID → index maps
        user_ids   = sorted(ratings_df['userId'].unique())
        item_ids   = sorted(ratings_df['movieId'].unique())
        user_idx   = {uid: i for i, uid in enumerate(user_ids)}
        self.item_idx = {iid: i for i, iid in enumerate(item_ids)}

        r_vals = ratings_df['rating'].values.astype(np.float32)
        r_rows = ratings_df['userId'].map(user_idx).values
        r_cols = ratings_df['movieId'].map(self.item_idx).values

        n_u = len(user_ids)
        n_i = len(item_ids)
        matrix = csr_matrix((r_vals, (r_rows, r_cols)), shape=(n_u, n_i))

        # Mean-center
        self._global_mean = float(r_vals.mean())
        mc = matrix.copy().astype(np.float64)
        mc.data -= self._global_mean

        # Truncated SVD
        k = min(n_factors, min(n_u, n_i) - 1)
        U, sigma, Vt = svds(mc, k=k)

        # Sort descending by singular value (svds returns ascending)
        order = np.argsort(sigma)[::-1]
        self.svd_U  = U[:, order]        # (n_users, k)
        self.svd_S  = sigma[order]       # (k,)
        self.svd_Vt = Vt[order, :]       # (k, n_items)

        print(f"  SVD: {k} factors | {n_u} users | {n_i} items")

    def _fold_in_user(self, user_ratings: dict) -> np.ndarray | None:
        """
        Fold-in: approximate latent vector for a new user by projecting
        their known ratings onto the item factor space.
        Returns SVD predicted scores for all movies (indexed by df row).
        """
        if self.svd_Vt is None or not self.item_idx:
            return None

        k          = self.svd_Vt.shape[0]
        user_vec   = np.zeros(k, dtype=np.float64)
        weight     = 0

        for mid, r in user_ratings.items():
            ii = self.item_idx.get(int(mid))
            if ii is not None:
                user_vec += (float(r) - self._global_mean) * self.svd_Vt[:, ii]
                weight   += 1

        if weight == 0:
            return None

        user_vec /= weight

        # Predict scores for every item: user_vec · Vt  (shape: n_items)
        raw = user_vec @ self.svd_Vt + self._global_mean   # (n_items,)

        # Map to DataFrame index
        scores = np.zeros(len(self.df), dtype=np.float64)
        for movie_id, ii in self.item_idx.items():
            di = self.movieid_to_dfidx.get(int(movie_id))
            if di is not None:
                scores[di] = np.clip(raw[ii], 0.5, 5.0)

        return scores

    # ── Model persistence ─────────────────────────────────────────────────────

    def save_model(self):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        payload = {
            'cosine_sim':   self.cosine_sim,
            'df':           self.df,
            'svd_U':        self.svd_U,
            'svd_S':        self.svd_S,
            'svd_Vt':       self.svd_Vt,
            'item_idx':     self.item_idx,
            'global_mean':  self._global_mean,
        }
        joblib.dump(payload, MODEL_PATH)
        print(f"  Model saved → {MODEL_PATH}")

    def load_model(self):
        d = joblib.load(MODEL_PATH)
        self.cosine_sim       = d['cosine_sim']
        self.df               = d['df']
        self.svd_U            = d.get('svd_U')
        self.svd_S            = d.get('svd_S')
        self.svd_Vt           = d.get('svd_Vt')
        self.item_idx         = d.get('item_idx', {})
        self._global_mean     = d.get('global_mean', 2.5)
        self.title_to_idx     = {t: i for i, t in enumerate(self.df['title'])}
        self.movieid_to_dfidx = {int(r['movieId']): i for i, r in self.df.iterrows()}
        print(f"  Model loaded ({len(self.df):,} films)")

    def initialize(self, force=False):
        print("Initializing CineNusa recommender...")
        self.load_data()
        self.build_content_model()

        if not force and os.path.exists(MODEL_PATH):
            try:
                self.load_model()
                print("Recommender ready (cached model).")
                return
            except Exception as e:
                print(f"  Cache invalid ({e}), retraining…")

        self.generate_synthetic_ratings()
        self.train_svd()
        self.save_model()
        print("Recommender ready.")

    # ── Recommendation API ────────────────────────────────────────────────────

    def get_similar_movies(self, title, n=8):
        if title not in self.title_to_idx:
            return pd.DataFrame()
        idx    = self.title_to_idx[title]
        scores = sorted(enumerate(self.cosine_sim[idx]), key=lambda x: x[1], reverse=True)[1:n+1]
        result = self.df.iloc[[s[0] for s in scores]].copy()
        result['similarity'] = [round(s[1] * 100, 1) for s in scores]
        return result

    def get_personalized_recommendations(self, user_ratings: dict, n=12):
        """
        Hybrid: 60% Content-Based + 40% SVD collaborative score.
        user_ratings: {movieId(int): rating(float 0.5–5)}
        """
        if not user_ratings:
            return self.get_top_rated(n)

        liked = {mid: r for mid, r in user_ratings.items() if r >= 2.5}
        if not liked:
            return self.get_top_rated(n)

        # Content-Based score
        cbf = np.zeros(len(self.df))
        for mid, r in liked.items():
            mask = self.df['movieId'] == int(mid)
            if mask.any():
                di   = self.df[mask].index[0]
                cbf += (r / 5.0) * self.cosine_sim[di]

        # SVD fold-in score
        svd_scores = self._fold_in_user(user_ratings)

        if svd_scores is not None:
            # Normalise SVD scores to [0,1]
            sv_min, sv_max = svd_scores.min(), svd_scores.max()
            if sv_max > sv_min:
                svd_norm = (svd_scores - sv_min) / (sv_max - sv_min)
            else:
                svd_norm = np.zeros_like(svd_scores)

            # Normalise CBF scores to [0,1]
            cbf_min, cbf_max = cbf.min(), cbf.max()
            if cbf_max > cbf_min:
                cbf_norm = (cbf - cbf_min) / (cbf_max - cbf_min)
            else:
                cbf_norm = cbf

            final = 0.6 * cbf_norm + 0.4 * svd_norm
        else:
            final = cbf

        rated_ids  = set(int(k) for k in user_ratings.keys())
        candidates = [
            (i, final[i])
            for i in range(len(self.df))
            if self.df.iloc[i]['movieId'] not in rated_ids
        ]
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_idx = [c[0] for c in candidates[:n]]

        result = self.df.iloc[top_idx].copy()
        result['predicted_rating'] = [round(candidates[j][1] * 5, 2) for j in range(len(top_idx))]
        return result

    def get_top_rated(self, n=20, min_votes=30):
        df = self.df.copy()
        C  = df['rating_norm'].mean()
        df['weighted_rating'] = (
            df['votes'] / (df['votes'] + min_votes) * df['rating_norm'] +
            min_votes / (df['votes'] + min_votes) * C
        )
        return df.nlargest(n, 'weighted_rating')

    def search(self, query, field='all', n=30):
        q = query.lower()
        if field == 'title':
            mask = self.df['title'].str.lower().str.contains(q, na=False)
        elif field == 'genre':
            mask = self.df['genre'].str.lower().str.contains(q, na=False)
        elif field == 'director':
            mask = self.df['director'].str.lower().str.contains(q, na=False)
        else:
            mask = (
                self.df['title'].str.lower().str.contains(q, na=False) |
                self.df['genre'].str.lower().str.contains(q, na=False) |
                self.df['director'].str.lower().str.contains(q, na=False) |
                self.df['stars'].str.lower().str.contains(q, na=False)
            )
        return self.df[mask].head(n)

    def get_by_id(self, movie_id):
        row = self.df[self.df['movieId'] == int(movie_id)]
        return row.iloc[0].to_dict() if len(row) else None

    def get_genres(self):
        genres = set()
        for g in self.df['genre'].dropna():
            for x in g.replace('|', ',').split(','):
                x = x.strip()
                if x and x != 'nan':
                    genres.add(x)
        return sorted(genres)

    def stats(self):
        return {
            'total_movies':  int(len(self.df)),
            'avg_rating':    round(float(self.df['rating'].mean()), 2),
            'total_ratings': int(len(self._syn_ratings)) if hasattr(self, '_syn_ratings') else 0,
            'genres_count':  int(len(self.get_genres())),
        }
