(function () {
  var root = document.documentElement;
  var btn = document.getElementById('theme');
  function current() {
    return root.dataset.theme ||
      (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }
  function label() { if (btn) btn.textContent = current() === 'dark' ? 'Светлая' : 'Тёмная'; }
  function save(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  label();
  if (btn) btn.addEventListener('click', function () {
    var t = current() === 'dark' ? 'light' : 'dark';
    root.dataset.theme = t; save('theme', t); label();
  });
  function fs(delta) {
    var v = parseFloat(getComputedStyle(root).getPropertyValue('--fs')) || 19;
    v = Math.min(26, Math.max(15, v + delta));
    root.style.setProperty('--fs', v + 'px'); save('fs', v);
  }
  var up = document.getElementById('fs-up'), down = document.getElementById('fs-down');
  if (up) up.addEventListener('click', function () { fs(1); });
  if (down) down.addEventListener('click', function () { fs(-1); });
  // главная: «по полкам» или «по времени написания», выбор запоминается
  var vs = document.getElementById('v-shelves'), vw = document.getElementById('v-written');
  var segs = document.querySelectorAll('.seg [data-view]');
  function view(v) {
    if (!vs || !vw) return;
    var w = v === 'written';
    vs.hidden = w; vw.hidden = !w;
    var ch = document.getElementById('chips'), wn = document.getElementById('wnote');
    if (ch) ch.hidden = w;
    if (wn) wn.hidden = !w;
    for (var j = 0; j < segs.length; j++)
      segs[j].setAttribute('aria-pressed', segs[j].getAttribute('data-view') === v ? 'true' : 'false');
  }
  if (vs && vw) {
    try { if (localStorage.getItem('view') === 'written') view('written'); } catch (e) {}
    for (var k = 0; k < segs.length; k++) segs[k].addEventListener('click', function () {
      var v = this.getAttribute('data-view'); view(v); save('view', v);
    });
  }
  // кнопка ▶ на плитке: главная тема цикла, играет одна за раз
  var audio = null, playing = null;
  function stop() {
    if (audio) audio.pause();
    if (playing) for (var q = document.querySelectorAll('.tplay[data-src="' + playing + '"]'), r = 0; r < q.length; r++)
      q[r].setAttribute('aria-pressed', 'false');
  }
  var pl = document.querySelectorAll('.tplay');
  for (var p = 0; p < pl.length; p++) pl[p].addEventListener('click', function () {
    var src = this.getAttribute('data-src');
    if (playing === src && audio && !audio.paused) { stop(); playing = null; return; }
    stop();
    if (!audio) { audio = new Audio(); audio.addEventListener('ended', function () { stop(); playing = null; }); }
    if (audio.getAttribute('src') !== src) audio.src = src;
    playing = src;
    var q = document.querySelectorAll('.tplay[data-src="' + src + '"]');
    for (var r = 0; r < q.length; r++) q[r].setAttribute('aria-pressed', 'true');
    var pr = audio.play();
    if (pr && pr.catch) pr.catch(function () { stop(); playing = null; });
  });
  // почта собирается на лету, чтобы её не подбирали автоматические сборщики адресов
  var m = document.querySelectorAll('[data-u][data-d]');
  for (var i = 0; i < m.length; i++) {
    var a = m[i].getAttribute('data-u') + '@' + m[i].getAttribute('data-d');
    m[i].innerHTML = '<a href="mailto:' + a + '">' + a + '</a>';
  }
})();
