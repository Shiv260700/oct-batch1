/* =====================================================================
   SQL Performance Workshop — tiny slide engine (no dependencies)
   Keys:  → / Space / PageDown  next step or slide
          ← / PageUp            back
          Home / End            first / last slide
          N  speaker notes      O  overview      F  fullscreen
          B  blank screen       ?  help
   Mark any element with class="step" to reveal it one click at a time.
   Put speaker notes in <aside class="notes-src"> inside a slide.
   <pre class="sql"> and <pre class="plan"> are coloured automatically.
   ===================================================================== */
(function () {
  const slides = Array.from(document.querySelectorAll('.slide'));
  const deckName = document.body.dataset.deck || document.title;
  let current = 0;

  /* ---------- build chrome ---------- */
  const progress = el('div', 'progress');
  const notes = el('div', 'notes');
  const overview = el('div', 'overview');
  const help = el('div', 'help');
  const chrome = el('div', 'chrome');
  chrome.innerHTML =
    '<button class="navbtn" data-act="prev" title="Back (←)">←</button>' +
    '<button class="navbtn" data-act="next" title="Next (→)">→</button>' +
    '<button class="navbtn" data-act="notes" title="Speaker notes (N)">Notes</button>' +
    '<button class="navbtn" data-act="overview" title="All slides (O)">Slides</button>' +
    '<button class="navbtn" data-act="full" title="Fullscreen (F)">⛶</button>';
  help.innerHTML =
    '<table>' +
    row('→  Space  PageDown', 'next step / slide') + row('←  PageUp', 'back') +
    row('Home  End', 'first / last slide') + row('N', 'speaker notes') +
    row('O', 'all slides') + row('F', 'fullscreen') + row('B', 'blank screen') +
    row('Ctrl/⌘ + P', 'print or save as PDF') + '</table>';
  document.body.append(progress, chrome, notes, overview, help);

  const blank = el('div');
  blank.style.cssText = 'position:fixed;inset:0;background:#000;z-index:60;display:none';
  document.body.append(blank);

  /* ---------- per-slide setup ---------- */
  slides.forEach((s, i) => {
    const foot = el('div', 'foot');
    foot.innerHTML = '<span>' + esc(deckName) + '</span><span>' + (i + 1) + ' / ' + slides.length + '</span>';
    s.append(foot);
    const b = el('button');
    const title = (s.querySelector('h1,h2') || {}).textContent || 'Slide ' + (i + 1);
    b.innerHTML = '<small>' + (i + 1) + '</small><span>' + esc(title.trim()) + '</span>';
    b.onclick = () => { go(i); toggle(overview, false); };
    overview.append(b);
  });

  document.querySelectorAll('pre.sql').forEach(pre => colour(pre, sqlRules));
  document.querySelectorAll('pre.plan').forEach(pre => colour(pre, planRules));

  /* ---------- navigation ---------- */
  function steps(s) { return Array.from(s.querySelectorAll('.step')); }

  function go(i, showAll) {
    i = Math.max(0, Math.min(slides.length - 1, i));
    slides[current].classList.remove('active');
    current = i;
    const s = slides[current];
    s.classList.add('active');
    steps(s).forEach(x => x.classList.toggle('shown', !!showAll));
    progress.style.width = ((current + 1) / slides.length * 100) + '%';
    const src = s.querySelector('aside.notes-src');
    notes.innerHTML = '<h4>Speaker notes · slide ' + (current + 1) + '</h4>' + (src ? src.innerHTML : '<p>No notes for this slide.</p>');
    overview.querySelectorAll('button').forEach((b, j) => b.classList.toggle('current', j === current));
    history.replaceState(null, '', '#' + (current + 1));
    const hook = s.dataset.onenter;
    if (hook && typeof window[hook] === 'function') window[hook](s);
  }

  function next() {
    const hidden = steps(slides[current]).filter(x => !x.classList.contains('shown'));
    if (hidden.length) { hidden[0].classList.add('shown'); return; }
    if (current < slides.length - 1) go(current + 1);
  }

  function prev() {
    const shown = steps(slides[current]).filter(x => x.classList.contains('shown'));
    if (shown.length) { shown[shown.length - 1].classList.remove('shown'); return; }
    if (current > 0) go(current - 1, true);
  }

  function fit() {
    const s = Math.min(window.innerWidth / 1280, window.innerHeight / 720) * 0.97;
    document.documentElement.style.setProperty('--scale', 'scale(' + s.toFixed(4) + ')');
  }

  function fullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen();
  }

  function toggle(node, force) { node.classList.toggle('open', force); }

  document.addEventListener('keydown', e => {
    if (e.target.closest('input, textarea, select')) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (['ArrowRight', 'ArrowDown', ' ', 'PageDown', 'Enter'].includes(k)) { e.preventDefault(); next(); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace'].includes(k)) { e.preventDefault(); prev(); }
    else if (k === 'Home') go(0);
    else if (k === 'End') go(slides.length - 1, true);
    else if (k === 'n' || k === 'N') toggle(notes);
    else if (k === 'o' || k === 'O') toggle(overview);
    else if (k === 'f' || k === 'F') fullscreen();
    else if (k === 'b' || k === 'B' || k === '.') blank.style.display = blank.style.display === 'none' ? 'block' : 'none';
    else if (k === '?') toggle(help);
    else if (k === 'Escape') { toggle(overview, false); toggle(help, false); blank.style.display = 'none'; }
  });

  chrome.addEventListener('click', e => {
    const act = (e.target.closest('button') || {}).dataset?.act;
    if (act === 'next') next();
    if (act === 'prev') prev();
    if (act === 'notes') toggle(notes);
    if (act === 'overview') toggle(overview);
    if (act === 'full') fullscreen();
  });

  let touchX = null;
  document.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
  document.addEventListener('touchend', e => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 50) (dx < 0 ? next : prev)();
    touchX = null;
  });

  window.addEventListener('resize', fit);
  fit();
  go(Math.max(0, (parseInt(location.hash.slice(1), 10) || 1) - 1));

  /* ---------- syntax colouring (works on text nodes, keeps <mark>) ---------- */
  function colour(pre, rules) {
    const walker = document.createTreeWalker(pre, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(n => {
      const html = rules(n.nodeValue);
      if (html === esc(n.nodeValue)) return;
      const span = document.createElement('span');
      span.innerHTML = html;
      n.replaceWith(...span.childNodes);
    });
  }

  function sqlRules(text) {
    const re = /(--[^\n]*)|('(?:[^']|'')*')|\b(\d+(?:\.\d+)?)\b|\b(SELECT|FROM|WHERE|AND|OR|NOT|IN|EXISTS|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|LATERAL|ON|USING|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|AS|DISTINCT|CASE|WHEN|THEN|ELSE|END|IS|NULL|BETWEEN|LIKE|ILIKE|UNION|ALL|EXCEPT|INTERSECT|WITH|MATERIALIZED|RECURSIVE|INSERT|INTO|VALUES|UPDATE|SET|DELETE|RETURNING|CREATE|OR REPLACE|DROP|ALTER|TABLE|INDEX|VIEW|STATISTICS|FUNCTION|PROCEDURE|RETURNS|LANGUAGE|BEGIN|COMMIT|ROLLBACK|DECLARE|RAISE|NOTICE|EXCEPTION|IF|ELSIF|LOOP|FOR|RETURN|QUERY|CALL|DO|EXPLAIN|ANALYZE|BUFFERS|VERBOSE|COSTS|TIMING|VACUUM|INCLUDE|DESC|ASC|NULLS|FIRST|LAST|OVER|PARTITION|ROW_NUMBER|COUNT|SUM|AVG|MIN|MAX|COALESCE|LOWER|UPPER|TIMESTAMP|DATE|INTERVAL|NUMERIC|TEXT|BIGINT|INT|INTEGER|BOOLEAN|TRUE|FALSE|PRIMARY|KEY|REFERENCES|CONSTRAINT|UNIQUE|CHECK|DEFAULT|GENERATED|ALWAYS|IDENTITY|LOCAL|RESET|SHOW|STABLE|IMMUTABLE|VOLATILE|STRICT|SECURITY|DEFINER|PERFORM|EXECUTE|FOUND|BRIN|GIN|ON CONFLICT)\b/gi;
    return esc(text).replace(re, (m, com, str, num, kw) => {
      if (com) return '<span class="com">' + com + '</span>';
      if (str) return '<span class="str">' + str + '</span>';
      if (num) return '<span class="num">' + num + '</span>';
      return '<span class="kw">' + m + '</span>';
    });
  }

  function planRules(text) {
    const nodesRe = /\b((?:Parallel |Partial |Finalize )?(?:Seq Scan|Index Only Scan|Index Scan Backward|Index Scan|Bitmap Heap Scan|Bitmap Index Scan|Hash (?:Semi |Anti |Right Semi |Right Anti |Right |Left |Full )?Join|Merge (?:Semi |Anti |Right |Left |Full )?Join|Nested Loop(?: Semi Join| Anti Join| Left Join)?|HashAggregate|GroupAggregate|MixedAggregate|Aggregate|Incremental Sort|Sort|Gather Merge|Gather|Limit|Materialize|Memoize|WindowAgg|Unique|Append|Subquery Scan|CTE Scan|Function Scan|Result|SetOp|HashSetOp|Hash|BitmapAnd|BitmapOr|ProjectSet|LockRows|ModifyTable|Update|Delete|Insert))\b(?! (?:Cond|Key|Method|Groups|Fetches|Blocks))/g;
    const metricRe = /\b(actual time|Rows Removed by Filter|Rows Removed by Join Filter|Rows Removed by Index Recheck|Heap Fetches|Heap Blocks|Buffers|Planning Time|Execution Time|Planning|Index Cond|Recheck Cond|Filter|Join Filter|Hash Cond|Merge Cond|Sort Key|Sort Method|Group Key|Batches|Memory Usage|Workers Planned|Workers Launched|Disk Usage|Cache Key|Hits|Misses|loops|SubPlan|InitPlan|Presorted Key|Full-sort Groups|Order By)\b/g;
    return esc(text)
      .replace(nodesRe, '<span class="node">$1</span>')
      .replace(metricRe, '<span class="kw">$1</span>');
  }

  /* ---------- helpers ---------- */
  function el(tag, cls) { const n = document.createElement(tag); if (cls) n.className = cls; return n; }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function row(k, v) { return '<tr><td><kbd>' + k + '</kbd></td><td>' + v + '</td></tr>'; }

  window.Deck = { go, next, prev };
})();
