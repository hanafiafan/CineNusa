/* CineNusa — main.js | Netflix × AI Tech Theme */
'use strict';

/* ══════════════════════════════════════════════════════════════════════
   GENRE COLORS (for buildCard placeholders)
   ══════════════════════════════════════════════════════════════════════ */
const GENRE_COLORS = {
  action:    '#7a1a10',
  adventure: '#7a4010',
  animation: '#4a1a7a',
  biography: '#0a4a3a',
  comedy:    '#0a4a1a',
  crime:     '#3a0a5a',
  drama:     '#1a2040',
  family:    '#0a3a6a',
  fantasy:   '#5a1a00',
  history:   '#3a2a20',
  horror:    '#5a0000',
  music:     '#6a0a30',
  romance:   '#6a0a40',
  'sci-fi':  '#00406a',
  thriller:  '#5a3200',
  war:       '#2a3540',
  musical:   '#5a0a30',
  mystery:   '#2a0a5a',
};

function genreColor(genre) {
  return GENRE_COLORS[(genre || '').toLowerCase().trim()] || '#18182a';
}

function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ══════════════════════════════════════════════════════════════════════
   LOADING SCREEN
   ══════════════════════════════════════════════════════════════════════ */
window.addEventListener('load', () => {
  const loader = document.getElementById('loader');
  if (!loader) return;
  setTimeout(() => loader.classList.add('gone'), 900);
  setTimeout(() => loader.remove(), 1500);
});

/* ══════════════════════════════════════════════════════════════════════
   NAVBAR — scrolled state
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const nav = document.getElementById('nav');
  if (!nav) return;
  const toggle = () => nav.classList.toggle('scrolled', window.scrollY > 50);
  toggle();
  window.addEventListener('scroll', toggle, { passive: true });
})();

/* ══════════════════════════════════════════════════════════════════════
   CUSTOM CURSOR
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const dot  = document.getElementById('cursor-dot');
  const ring = document.getElementById('cursor-ring');
  if (!dot || !ring) return;

  let mx = -200, my = -200, rx = -200, ry = -200;

  document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });
  document.addEventListener('mousedown', () => document.body.classList.add('cursor-click'));
  document.addEventListener('mouseup',   () => document.body.classList.remove('cursor-click'));

  const interactiveEls = 'a,button,input,select,textarea,[role="button"],.nf-card,.fcard,.mood-chip,.swipe-btn';
  document.addEventListener('mouseover', e => {
    if (e.target.closest(interactiveEls)) document.body.classList.add('cursor-hover');
  });
  document.addEventListener('mouseout', e => {
    if (e.target.closest(interactiveEls)) document.body.classList.remove('cursor-hover');
  });

  function lerp(a, b, t) { return a + (b - a) * t; }

  function loop() {
    dot.style.left  = mx + 'px';
    dot.style.top   = my + 'px';
    rx = lerp(rx, mx, 0.13);
    ry = lerp(ry, my, 0.13);
    ring.style.left = rx + 'px';
    ring.style.top  = ry + 'px';
    requestAnimationFrame(loop);
  }
  loop();
})();

/* ══════════════════════════════════════════════════════════════════════
   NEURAL NETWORK CANVAS (hero background decoration)
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const canvas = document.getElementById('neural-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const N   = 32;
  const DIST = 170;
  const SPD  = 0.18;
  let W, H, nodes;

  function resize() {
    W = canvas.width  = canvas.offsetWidth  || window.innerWidth;
    H = canvas.height = canvas.offsetHeight || window.innerHeight;
  }

  function init() {
    resize();
    nodes = Array.from({ length: N }, () => ({
      x:  Math.random() * W,
      y:  Math.random() * H,
      vx: (Math.random() - 0.5) * SPD,
      vy: (Math.random() - 0.5) * SPD,
      r:  1.2 + Math.random() * 1.8,
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);

    /* move */
    nodes.forEach(n => {
      n.x += n.vx; n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;
    });

    /* edges */
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx   = nodes[i].x - nodes[j].x;
        const dy   = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < DIST) {
          const a = (1 - dist / DIST) * 0.45;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.strokeStyle = `rgba(0,212,255,${a})`;
          ctx.lineWidth   = 0.7;
          ctx.stroke();
        }
      }
    }

    /* nodes */
    nodes.forEach(n => {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0,212,255,0.75)';
      ctx.fill();
    });

    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', () => {
    resize();
    nodes.forEach(n => {
      n.x = Math.min(n.x, W);
      n.y = Math.min(n.y, H);
    });
  });

  init();
  draw();
})();

/* ══════════════════════════════════════════════════════════════════════
   BUILD CARD HTML (used by lazy rows + mood filter)
   ══════════════════════════════════════════════════════════════════════ */
function buildCard(m) {
  const yr    = (m.year && m.year !== 'nan' && m.year !== 'None') ? m.year : '';
  const rat   = parseFloat(m.rating || 0).toFixed(1);
  const genre = (m.genre || '').split(',')[0].trim();
  const hasPoster = m.poster_url &&
                    m.poster_url !== 'nan' &&
                    m.poster_url !== 'None' &&
                    String(m.poster_url).startsWith('http');
  const short = m.title.length > 24 ? m.title.slice(0, 24) + '…' : m.title;

  const posterHtml = hasPoster
    ? `<img src="${escHtml(m.poster_url)}" alt="${escHtml(m.title)}" loading="lazy" onerror="this.style.display='none'">`
    : `<div class="nf-poster-ph"><i class="bi bi-film"></i><span>${escHtml(short)}</span></div>`;

  return `
    <article class="nf-card">
      <a href="/movie/${escHtml(String(m.movieId))}" class="nf-card-link">
        <div class="nf-card-poster">
          ${posterHtml}
          <div class="nf-card-rating"><i class="bi bi-star-fill"></i> ${escHtml(rat)}</div>
        </div>
        <div class="nf-card-info">
          <div class="nf-card-title">${escHtml(m.title)}</div>
          <div class="nf-card-meta">
            ${yr ? `<span>${escHtml(yr)}</span>` : ''}
            ${genre ? `<span class="nf-card-genre">${escHtml(genre)}</span>` : ''}
          </div>
        </div>
      </a>
    </article>`;
}

/* Keep applyCardColors as no-op for backward compat */
function applyCardColors(root) { /* no-op — dark theme uses genre colors via CSS */ }

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
   NAV AUTOCOMPLETE
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
                <i class="bi bi-film"></i>
              </div>
              <div class="ac-item-info">
                <div class="ac-item-title">${escHtml(m.title)}</div>
                <div class="ac-item-meta">${yr}${yr && g ? ' · ' : ''}${escHtml(g)}</div>
              </div>
              <span class="ac-item-rating"><i class="bi bi-star-fill"></i> ${escHtml(rat)}</span>
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
   SCROLL REVEAL — nf-card + fcard entrance animation
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        /* override animation: keep opacity 1 */
        e.target.style.opacity = '1';
        e.target.style.animation = 'none';
        io.unobserve(e.target);
      }
    });
  }, { rootMargin: '0px 0px -30px 0px', threshold: 0.05 });

  function observeCards() {
    document.querySelectorAll('.nf-card:not(.visible), .fcard:not(.visible)').forEach(c => {
      c.style.opacity = '0';
      io.observe(c);
    });
  }
  observeCards();

  /* Re-observe when new cards injected (lazy rows) */
  new MutationObserver(observeCards).observe(document.body, { childList: true, subtree: true });
})();

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

/* ══════════════════════════════════════════════════════════════════════
   SWIPE PAGE touch support
   ══════════════════════════════════════════════════════════════════════ */
(function() {
  const arena = document.getElementById('swipe-arena');
  if (!arena) return;
  let startX = null;
  arena.addEventListener('touchstart', e => { startX = e.touches[0].clientX; }, { passive: true });
  arena.addEventListener('touchend', e => {
    if (startX === null) return;
    const dx = e.changedTouches[0].clientX - startX;
    startX = null;
    if (Math.abs(dx) < 50) return;
    const top = arena.querySelector('.is-top');
    if (!top) return;
    if (dx > 0) top.querySelector('.swipe-btn.like')?.click();
    else        top.querySelector('.swipe-btn.skip')?.click();
  });
})();
