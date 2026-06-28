/* CineNusa — main.js | Neubrutalism × Full Animation */
'use strict';

/* ══════════════════════════════════════════════════════════════════════
   GENRE COLORS
   ══════════════════════════════════════════════════════════════════════ */
const GENRE_COLORS = {
  action:    '#CC2200',
  adventure: '#CC6600',
  animation: '#7B2FBE',
  biography: '#0A7A5A',
  comedy:    '#1A8C3A',
  crime:     '#6A1A8C',
  drama:     '#2C3E60',
  family:    '#1A5C9A',
  fantasy:   '#A03000',
  history:   '#5D4037',
  horror:    '#8B0000',
  music:     '#AD1457',
  romance:   '#C0156E',
  'sci-fi':  '#006A80',
  thriller:  '#8C5200',
  war:       '#455A64',
  musical:   '#880E4F',
  mystery:   '#4A148C',
};

function genreColor(genre) {
  return GENRE_COLORS[(genre || '').toLowerCase().trim()] || '#1a1a1a';
}

/* ══════════════════════════════════════════════════════════════════════
   LOADING SCREEN
   ══════════════════════════════════════════════════════════════════════ */
window.addEventListener('load', () => {
  const loader = document.getElementById('loader');
  if (!loader) return;
  setTimeout(() => loader.classList.add('gone'), 900);
  setTimeout(() => loader.remove(), 1450);
});

/* ══════════════════════════════════════════════════════════════════════
   CUSTOM CURSOR
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const dot  = document.getElementById('cursor-dot');
  const ring = document.getElementById('cursor-ring');
  if (!dot || !ring) return;

  let mx = -200, my = -200, rx = -200, ry = -200;
  let raf;

  document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });
  document.addEventListener('mousedown', () => document.body.classList.add('cursor-click'));
  document.addEventListener('mouseup',   () => document.body.classList.remove('cursor-click'));

  function interactiveEls() {
    return 'a,button,input,select,textarea,[role="button"],.fcard,.mood-btn,.swipe-btn,.swipe-card';
  }

  document.addEventListener('mouseover', e => {
    if (e.target.closest(interactiveEls())) {
      document.body.classList.add('cursor-hover');
    }
  });
  document.addEventListener('mouseout', e => {
    if (e.target.closest(interactiveEls())) {
      document.body.classList.remove('cursor-hover');
    }
  });

  function lerp(a, b, t) { return a + (b - a) * t; }

  function loop() {
    dot.style.left  = mx + 'px';
    dot.style.top   = my + 'px';
    rx = lerp(rx, mx, 0.14);
    ry = lerp(ry, my, 0.14);
    ring.style.left = rx + 'px';
    ring.style.top  = ry + 'px';
    raf = requestAnimationFrame(loop);
  }
  loop();
})();

/* ══════════════════════════════════════════════════════════════════════
   CONFETTI
   ══════════════════════════════════════════════════════════════════════ */
function launchConfetti() {
  const canvas = document.getElementById('confetti-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;

  const colors = ['#FFE500','#0D0D0D','#FF4444','#22CC55','#00BBDD','#FF69B4'];
  const pieces = Array.from({ length: 120 }, () => ({
    x:  Math.random() * canvas.width,
    y:  -10 - Math.random() * 150,
    r:  4 + Math.random() * 6,
    d:  2 + Math.random() * 4,
    vx: (Math.random() - .5) * 3,
    color: colors[Math.floor(Math.random() * colors.length)],
    rot: Math.random() * 360,
    rotV: (Math.random() - .5) * 6,
    shape: Math.random() > .5 ? 'rect' : 'circle',
  }));

  let frame = 0;
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    pieces.forEach(p => {
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot * Math.PI / 180);
      ctx.fillStyle = p.color;
      if (p.shape === 'rect') ctx.fillRect(-p.r, -p.r / 2, p.r * 2, p.r);
      else { ctx.beginPath(); ctx.arc(0, 0, p.r / 2, 0, Math.PI * 2); ctx.fill(); }
      ctx.restore();
      p.y  += p.d;
      p.x  += p.vx;
      p.rot += p.rotV;
      if (p.y > canvas.height + 20) p.y = -20;
    });
    frame++;
    if (frame < 200) requestAnimationFrame(draw);
    else ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
  draw();
}

/* ══════════════════════════════════════════════════════════════════════
   CARD COLORS (neubrutalism version)
   Apply genre background color to .fcard-bg and .fcard-colorbar elements
   ══════════════════════════════════════════════════════════════════════ */
function applyCardColors(root) {
  const scope = root || document;
  scope && scope.querySelectorAll('.fcard-bg[data-genre]').forEach(el => {
    el.style.background = genreColor(el.dataset.genre);
  });
  scope && scope.querySelectorAll('.fcard-colorbar[data-genre]').forEach(el => {
    el.style.background = genreColor(el.dataset.genre);
  });
}

/* Run on every page */
applyCardColors();

/* ══════════════════════════════════════════════════════════════════════
   BUILD CARD HTML (for JS-rendered rows)
   ══════════════════════════════════════════════════════════════════════ */
function buildCard(m) {
  const yr    = (m.year && m.year !== 'nan' && m.year !== 'None') ? m.year : '';
  const rat   = parseFloat(m.rating || 0).toFixed(1);
  const genre = (m.genre || '').split(',')[0].trim();
  const col   = genreColor(genre);
  return `
    <article class="fcard">
      <a href="/movie/${m.movieId}" style="display:block;color:inherit">
        <div class="fcard-poster">
          <div class="fcard-bg" style="background:${escHtml(col)}">
            <div class="fcard-bg-title">${escHtml(m.title)}</div>
            ${yr ? `<div class="fcard-bg-year">${escHtml(yr)}</div>` : ''}
            <div class="fcard-bg-icon"><i class="bi bi-film"></i></div>
          </div>
          <div class="fcard-colorbar" style="background:${escHtml(col)}"></div>
          <div class="fcard-overlay">
            <div class="fcard-rating"><i class="bi bi-star-fill"></i> ${escHtml(rat)}</div>
            ${genre ? `<div class="fcard-genre-label">${escHtml(genre)}</div>` : ''}
          </div>
        </div>
        <div class="fcard-label">
          <div class="fcard-name">${escHtml(m.title)}</div>
          <div class="fcard-meta">${escHtml(yr)}</div>
        </div>
      </a>
    </article>`;
}

function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ══════════════════════════════════════════════════════════════════════
   DRAG-TO-SCROLL on film rows
   ══════════════════════════════════════════════════════════════════════ */
document.querySelectorAll('.film-row').forEach(row => {
  let down = false, startX, scrollLeft;
  row.addEventListener('mousedown', e => {
    if (e.target.closest('a,button')) return;
    down = true;
    startX     = e.pageX - row.offsetLeft;
    scrollLeft = row.scrollLeft;
    row.style.userSelect = 'none';
  });
  const up = () => { down = false; row.style.userSelect = ''; };
  row.addEventListener('mouseleave', up);
  row.addEventListener('mouseup',   up);
  row.addEventListener('mousemove', e => {
    if (!down) return;
    e.preventDefault();
    row.scrollLeft = scrollLeft - (e.pageX - row.offsetLeft - startX) * 1.5;
  });
});

/* ══════════════════════════════════════════════════════════════════════
   NAV AUTOCOMPLETE (rich preview)
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const input = document.getElementById('nav-q');
  const box   = document.getElementById('autocomplete-box');
  const btn   = document.getElementById('nav-search-btn');
  if (!input || !box) return;

  let timer;

  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { box.classList.remove('open'); box.innerHTML = ''; return; }
    timer = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(q)}&n=8`)
        .then(r => r.json())
        .then(data => {
          if (!data.length) { box.classList.remove('open'); return; }
          box.innerHTML = data.map(m => {
            const g   = (m.genre || '').split(',')[0].trim();
            const col = genreColor(g);
            const rat = parseFloat(m.rating || 0).toFixed(1);
            const yr  = (m.year && m.year !== 'nan') ? m.year : '';
            return `<div class="ac-item" data-id="${m.movieId}" tabindex="0">
              <div class="ac-item-poster" style="background:${escHtml(col)}">
                <span style="font-size:.9rem;opacity:.5">🎬</span>
              </div>
              <div class="ac-item-info">
                <div class="ac-item-title">${escHtml(m.title)}</div>
                <div class="ac-item-meta">${yr}${yr && g ? ' · ' : ''}${escHtml(g)}</div>
              </div>
              <span class="ac-item-rating">⭐ ${escHtml(rat)}</span>
            </div>`;
          }).join('');
          box.classList.add('open');
        })
        .catch(() => box.classList.remove('open'));
    }, 180);
  });

  box.addEventListener('click', e => {
    const item = e.target.closest('.ac-item');
    if (item) location.href = `/movie/${item.dataset.id}`;
  });

  if (btn) {
    btn.addEventListener('click', () => {
      const q = input.value.trim();
      if (q) location.href = `/search?q=${encodeURIComponent(q)}`;
    });
  }

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const q = input.value.trim();
      if (q) location.href = `/search?q=${encodeURIComponent(q)}`;
    }
    if (e.key === 'Escape') box.classList.remove('open');
    if (e.key === 'ArrowDown') { e.preventDefault(); box.querySelector('.ac-item')?.focus(); }
  });

  box.addEventListener('keydown', e => {
    const f = document.activeElement;
    if (e.key === 'ArrowDown') { e.preventDefault(); f.nextElementSibling?.focus(); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); (f.previousElementSibling || input).focus(); }
    if (e.key === 'Enter' && f.dataset.id) location.href = `/movie/${f.dataset.id}`;
    if (e.key === 'Escape')    { box.classList.remove('open'); input.focus(); }
  });

  document.addEventListener('click', e => {
    if (!input.contains(e.target) && !box.contains(e.target)) box.classList.remove('open');
  });
})();

/* ══════════════════════════════════════════════════════════════════════
   STAR RATING (detail page)
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const stars  = document.querySelector('.stars');
  if (!stars) return;
  const halves = stars.querySelectorAll('.star-half');
  const hidden = document.getElementById('selected-rating');
  let selected = parseFloat(stars.dataset.selected) || 0;

  function paint(v) {
    halves.forEach(h => h.classList.toggle('star-half--filled', parseFloat(h.dataset.val) <= v));
  }
  halves.forEach(h => {
    h.addEventListener('mouseenter', () => paint(parseFloat(h.dataset.val)));
    h.addEventListener('click', () => {
      selected = parseFloat(h.dataset.val);
      if (hidden) hidden.value = selected;
      paint(selected);
    });
  });
  stars.addEventListener('mouseleave', () => paint(selected));
  paint(selected);
})();

/* ══════════════════════════════════════════════════════════════════════
   FLASH DISMISS
   ══════════════════════════════════════════════════════════════════════ */
document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity .3s, transform .3s';
    el.style.opacity    = '0';
    el.style.transform  = 'translateX(16px)';
    setTimeout(() => el.remove(), 320);
  }, 4200);
});

/* ══════════════════════════════════════════════════════════════════════
   PAGE TRANSITION (fade on link click)
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const style = document.createElement('style');
  style.textContent = '.page-fade-out { animation: pageFadeOut .2s ease forwards } @keyframes pageFadeOut { to { opacity:0; transform:translateY(-6px) } }';
  document.head.appendChild(style);

  document.addEventListener('click', e => {
    const a = e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('javascript') || e.ctrlKey || e.metaKey) return;
    if (a.hasAttribute('download') || a.target === '_blank') return;
    e.preventDefault();
    document.body.classList.add('page-fade-out');
    setTimeout(() => { location.href = href; }, 200);
  });
})();

/* ══════════════════════════════════════════════════════════════════════
   SCROLL REVEAL (fcard entrance animation)
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const style = document.createElement('style');
  style.textContent = `
    .fcard { opacity: 0; transform: translateY(18px); transition: opacity .35s ease, transform .35s ease }
    .fcard.visible { opacity: 1; transform: none }
  `;
  document.head.appendChild(style);

  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -40px 0px', threshold: 0.1 });

  function observeCards() {
    document.querySelectorAll('.fcard:not(.visible)').forEach(c => io.observe(c));
  }
  observeCards();

  /* Re-observe when new cards are added (lazy rows) */
  const mo = new MutationObserver(observeCards);
  mo.observe(document.body, { childList: true, subtree: true });
})();

/* ══════════════════════════════════════════════════════════════════════
   TICKER duplicate for seamless animation
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const ticker = document.getElementById('ticker');
  if (!ticker) return;
  /* Items already duplicated in template for seamless loop */
})();

/* ══════════════════════════════════════════════════════════════════════
   FCARD hover tilt (subtle 3D effect on desktop)
   ══════════════════════════════════════════════════════════════════════ */
document.addEventListener('mousemove', e => {
  const card = e.target.closest('.fcard');
  if (!card) return;
  const rect = card.getBoundingClientRect();
  const cx = rect.left + rect.width  / 2;
  const cy = rect.top  + rect.height / 2;
  const dx = (e.clientX - cx) / rect.width;
  const dy = (e.clientY - cy) / rect.height;
  card.querySelector('.fcard-inner') && (card.querySelector('.fcard-inner').style.transform =
    `translate(-3px,-3px) rotateX(${-dy * 5}deg) rotateY(${dx * 5}deg)`);
});
document.addEventListener('mouseleave', e => {
  const card = e.target.closest('.fcard');
  if (card && card.querySelector('.fcard-inner')) {
    card.querySelector('.fcard-inner').style.transform = '';
  }
}, true);

/* ══════════════════════════════════════════════════════════════════════
   IMG FADE-IN
   ══════════════════════════════════════════════════════════════════════ */
document.querySelectorAll('img[loading="lazy"]').forEach(img => {
  img.style.opacity    = '0';
  img.style.transition = 'opacity .4s';
  const show = () => { img.style.opacity = '1'; };
  img.addEventListener('load', show);
  if (img.complete) show();
});
