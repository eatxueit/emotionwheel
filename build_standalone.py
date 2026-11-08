"""
Builds dist/feelings-wheel-standalone.html from src/feelings-wheel.html.

    python build_standalone.py

The Claude version stores data in Claude's per-account storage and saves files
through Claude's save prompt. The standalone version:
  - keeps everything in a SQLite database inside the page (sql.js),
    saved automatically in the browser, optionally linked to a .sqlite file on disk
  - saves exports as ordinary browser downloads
  - bundles p5.js, jsPDF, sql.js and the Courier Prime font so it works offline
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
VENDOR = ROOT / 'vendor'
LIBS = {
    'p5': VENDOR / 'p5.min.js',
    'jspdf': VENDOR / 'jspdf.umd.min.js',
    'sqljs': VENDOR / 'sql-asm.js',
}

s = (ROOT / 'src' / 'feelings-wheel.html').read_text()


def rep(a, b, count=1):
    global s
    if a not in s:
        raise SystemExit('pattern not found:\n' + a[:200])
    s = s.replace(a, b, count)


def inline(path):
    code = path.read_text()
    assert '</script' not in code.lower()
    return '<script>\n' + code + '\n</script>'


# ---------------------------------------------------------------- head and libraries
rep('family=Courier+Prime:ital,wght@0,400;1,400&family=Figtree', 'family=Figtree')
rep('<script src="https://cdn.jsdelivr.net/npm/p5@1.11.11/lib/p5.min.js"></script>',
    inline(LIBS['p5']))
rep('<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>',
    inline(LIBS['jspdf']) + '\n' + inline(LIBS['sqljs']))

# the typewriter font comes from the embedded copy, so it works offline
rep('''window.COURIER_PRIME_TTF = {''', '''window.COURIER_PRIME_TTF = {''')
s = s.replace('''</script>
<script>
/*
  TypewriterBox:''', '''</script>
<script>
// register the embedded Courier Prime with the browser (no internet needed)
(function () {
  if (!window.FontFace || !document.fonts) return;
  function buf(b64) {
    var bin = atob(b64), out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out.buffer;
  }
  var faces = [['italic', 'italic', '400'], ['normal', 'normal', '400'], ['bold', 'normal', '700']];
  faces.forEach(function (f) {
    try {
      var face = new FontFace('Courier Prime', buf(window.COURIER_PRIME_TTF[f[0]]), { style: f[1], weight: f[2] });
      document.fonts.add(face);
      face.load();
    } catch (e) {}
  });
})();
</script>
<script>
/*
  TypewriterBox:''', 1)
assert 'register the embedded Courier Prime' in s

# ---------------------------------------------------------------- copy
rep("Notes save as you type and only you can read them.",
    "Notes save as you type and stay on this computer.")

# ---------------------------------------------------------------- data section (replaces "Export everything")
rep('''  <section class="export-all" id="export-all" hidden aria-labelledby="export-all-title">
    <div class="export-all-text">
      <h2 id="export-all-title">Export everything</h2>
      <p>All your colors and notes in one file: a PDF with the colored wheel and every note typed out, a plain text file, or a SQLite database.</p>
    </div>
    <div class="export-all-row">
      <button type="button" class="btn" id="all-pdf">PDF</button>
      <button type="button" class="btn" id="all-txt">Text file</button>
      <button type="button" class="btn" id="all-sqlite">SQLite database (.zip)</button>
      <span class="export-all-msg" id="all-msg" role="status" aria-live="polite"></span>
    </div>
  </section>''', '''  <section class="export-all" id="export-all" aria-labelledby="data-title">
    <div class="export-all-text">
      <h2 id="data-title">Your data</h2>
      <p>Your colors and notes live in a SQLite database inside this page. It saves automatically in this browser. To keep a copy on your disk that updates as you go, link it to a file.</p>
    </div>
    <div class="export-all-row">
      <span class="store-state" id="store-state">Loading…</span>
    </div>
    <div class="export-all-row">
      <button type="button" class="btn" id="store-link" hidden>Save to a file on this computer…</button>
      <button type="button" class="btn" id="store-reconnect" hidden>Reconnect</button>
      <button type="button" class="btn" id="store-unlink" hidden>Stop saving to the file</button>
      <button type="button" class="btn" id="store-open">Open a database file…</button>
      <input type="file" id="store-file" accept=".sqlite,.sqlite3,.db,application/vnd.sqlite3,application/x-sqlite3" hidden>
      <span class="export-all-msg" id="store-msg" role="status" aria-live="polite"></span>
    </div>
    <div class="export-all-row" id="store-confirm" hidden>
      <span class="ask" id="store-confirm-text"></span>
      <button type="button" class="btn danger" id="store-confirm-yes">Replace</button>
      <button type="button" class="btn" id="store-confirm-no">Cancel</button>
    </div>

    <div class="export-all-text">
      <h2 id="export-all-title">Export everything</h2>
      <p>A PDF with the colored wheel and every note typed out, a plain text file, or the SQLite database itself.</p>
    </div>
    <div class="export-all-row">
      <button type="button" class="btn" id="all-pdf">PDF</button>
      <button type="button" class="btn" id="all-txt">Text file</button>
      <button type="button" class="btn" id="all-sqlite">SQLite database</button>
      <span class="export-all-msg" id="all-msg" role="status" aria-live="polite"></span>
    </div>
  </section>''')
rep('''  .export-all-msg { color: var(--muted); font-size: 0.85rem; }''',
    '''  .export-all-msg { color: var(--muted); font-size: 0.85rem; }
  .store-state { font-size: 0.9rem; font-weight: 600; }
  .export-all .ask { font-size: 0.9rem; font-weight: 600; }
  .export-all-text + .export-all-row { margin-top: -2px; }
  .export-all-row + .export-all-text { margin-top: 14px; }''')
rep('''<div class="export" id="export" hidden>''', '''<div class="export" id="export">''')

# ---------------------------------------------------------------- downloads: ordinary browser downloads
rep('''  var downloads = null;
  var note = document.getElementById('export-note');''', '''  // ordinary browser downloads (the standalone page has no save prompt to go through)
  var downloads = {
    save: function (req) {
      return new Promise(function (resolve) {
        var blob = req.data instanceof Blob ? req.data : new Blob([req.data], { type: 'text/plain;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url; a.download = req.filename; a.rel = 'noopener';
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
        resolve({ status: 'saved' });
      });
    }
  };
  var note = document.getElementById('export-note');''')
rep('''  var downloadsAsked = false;
  function initDownloads() {
    if (downloadsAsked || !window.claude || typeof window.claude.use !== 'function') return;
    downloadsAsked = true;
    window.claude.use('downloads').then(function (d) {
      downloads = d;
      document.getElementById('export').hidden = !d;
      refreshNoteExport();
      refreshExportAll();
    }).catch(function () {});
  }
  initDownloads();
  window.addEventListener('load', initDownloads);''', '')
s = s.replace("note.textContent = 'Saved';", "note.textContent = 'Downloaded';")
s = s.replace("noteExp.msg.textContent = 'Saved';", "noteExp.msg.textContent = 'Downloaded';")
s = s.replace("all.msg.textContent = 'Saved'; });", "all.msg.textContent = 'Downloaded'; });")

# ---------------------------------------------------------------- colors: stored in the database
rep('''  var STORE_KEY = 'feelings-wheel-picks';
  var state = { mode: 0, picks: {} };   // picks: "level:index" -> "#rrggbb"
  var current = null;                   // { level, idx }
  try { var saved = JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); if (saved && typeof saved === 'object') state.picks = saved; } catch (e) {}
  function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(state.picks)); } catch (e) {} }''',
    '''  var state = { mode: 0, picks: {} };   // picks: "level:index" -> "#rrggbb"
  var current = null;                   // { level, idx }
  function save() { storeColors(); }   // colors go into the page's SQLite database''')

# ---------------------------------------------------------------- notes: stored in the database
rep('''  // Saved in this page's private per-account storage when it is available
  // (one document per feeling under data/users/<your id>/), otherwise in this browser.
  var NOTES_KEY = 'feelings-wheel-notes';
  var notes = {};            // "level:index" -> text
  var notesDb = null;        // collection reference when account storage is available
  var notesWhere = 'none';   // 'account' | 'browser' | 'none'
  var pendingTimer = null, pendingKey = null;
  var writeChains = {};      // one write at a time per note document''', '''  // Saved in the page's SQLite database (see "storage" below).
  var notes = {};            // "level:index" -> text
  var pendingTimer = null, pendingKey = null;''')

rep('''  function savedLabel() {
    return notesWhere === 'account' ? 'Saved to your account' : 'Saved in this browser only';
  }

  function writeNote(key, text) {
    if (notesWhere === 'account' && notesDb) {
      var ref = notesDb.doc(docIdFor(key));
      var parts = key.split(':');
      var prev = writeChains[key] || Promise.resolve();
      var next = prev.catch(function () {}).then(function () {
        return text
          ? ref.set({ level: +parts[0], index: +parts[1], text: text, updatedAt: new Date().toISOString() })
          : ref.delete();
      });
      writeChains[key] = next;
      next.then(function () {
        if (pendingKey === null) notesEl.status.textContent = savedLabel();
      }).catch(function (err) {
        notesEl.status.textContent = 'Could not save this note. Your text is still here; keep typing to try again.';
        console.error('note save failed', err);
      });
    } else {
      try { localStorage.setItem(NOTES_KEY, JSON.stringify(notes)); notesEl.status.textContent = savedLabel(); }
      catch (e) { notesEl.status.textContent = 'This browser is not keeping notes. Copy anything you want to keep.'; }
    }
  }''', '''  function savedLabel() { return storeLabel(); }

  function writeNote(key, text) {
    if (!sdb) { notesEl.status.textContent = 'Still opening the database…'; return; }
    storeNote(key, text);
    notesEl.status.textContent = savedLabel();
  }''')

# replace the account-storage loader with the SQLite store
a = s.index('  function useBrowserNotes() {')
b = s.index('  el.picker.addEventListener(\'input\'')
s = s[:a] + r'''  // ================= storage: a SQLite database inside the page =================
  // Tables (the same shape as the SQLite export):
  //   feelings(id, ring, name, parent_id, core, path, default_color, chosen_color, shown_color, added_at)
  //     ring is core, middle, outer, or added (a word you added; parent_id is its outer feeling)
  //   notes(feeling_id, text, typed_layout, updated_at)
  //   meta(key, value)
  // A copy is kept in this browser's local storage after every change. In browsers that allow it
  // (Chrome, Edge), the database can also be linked to a .sqlite file on disk that is rewritten
  // after every change.
  var DB_KEY = 'feelings-wheel-sqlite';
  var SQL = null, sdb = null, linked = null, persistTimer = null, browserOk = true, fileOk = true;
  var canLink = typeof window.showSaveFilePicker === 'function';

  var storeEl = {
    state: document.getElementById('store-state'),
    msg: document.getElementById('store-msg'),
    link: document.getElementById('store-link'),
    reconnect: document.getElementById('store-reconnect'),
    unlink: document.getElementById('store-unlink'),
    open: document.getElementById('store-open'),
    file: document.getElementById('store-file'),
    confirm: document.getElementById('store-confirm'),
    confirmText: document.getElementById('store-confirm-text'),
    yes: document.getElementById('store-confirm-yes'),
    no: document.getElementById('store-confirm-no')
  };

  function feelingsTable(name) {
    return "CREATE TABLE IF NOT EXISTS " + name + " (" +
      "  id INTEGER PRIMARY KEY," +
      "  ring TEXT NOT NULL CHECK (ring IN ('core','middle','outer','added'))," +
      "  name TEXT NOT NULL," +
      "  parent_id INTEGER REFERENCES feelings(id)," +
      "  core TEXT NOT NULL," +
      "  path TEXT NOT NULL," +
      "  default_color TEXT NOT NULL," +
      "  chosen_color TEXT," +
      "  shown_color TEXT NOT NULL," +
      "  added_at TEXT" +
      ");";
  }
  var SCHEMA =
    feelingsTable('feelings') +
    "CREATE TABLE IF NOT EXISTS notes (" +
    "  feeling_id INTEGER PRIMARY KEY REFERENCES feelings(id)," +
    "  text TEXT NOT NULL," +
    "  typed_layout TEXT NOT NULL," +
    "  updated_at TEXT" +
    ");" +
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);";

  // database ids come from feelingId() and keyOfId() in the page's export code

  function toB64(bytes) {
    var out = '', CH = 0x8000;
    for (var i = 0; i < bytes.length; i += CH) out += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
    return btoa(out);
  }
  function fromB64(str) {
    var bin = atob(str), out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  function metaGet(k) {
    var r = sdb.exec('SELECT value FROM meta WHERE key = ?', [k]);
    return r.length ? r[0].values[0][0] : null;
  }
  function metaSet(k, v) { sdb.run('INSERT OR REPLACE INTO meta VALUES (?, ?)', [k, v]); }

  var COLUMNS = 'id, ring, name, parent_id, core, path, default_color, chosen_color, shown_color';

  function ensureFeelings() {
    sdb.run(SCHEMA);
    // databases from before added words: rebuild the feelings table so it accepts them
    var def = sdb.exec("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'feelings'");
    if (def.length && def[0].values[0][0].indexOf("'added'") < 0) {
      sdb.run('BEGIN;' + feelingsTable('feelings_new') +
              'INSERT INTO feelings_new (' + COLUMNS + ') SELECT ' + COLUMNS + ' FROM feelings;' +
              'DROP TABLE feelings; ALTER TABLE feelings_new RENAME TO feelings; COMMIT;');
    }
    var n = sdb.exec('SELECT COUNT(*) FROM feelings WHERE id <= 114')[0].values[0][0];
    if (n >= 114) return;
    var ins = sdb.prepare('INSERT OR IGNORE INTO feelings (' + COLUMNS + ') VALUES (?,?,?,?,?,?,?,?,?)');
    allFeelings().forEach(function (f) {
      if (f.level > 3) return;
      var pk = parentKeyOf(f);
      ins.run([feelingId(f.key), f.ring, f.name, pk ? feelingId(pk) : null, f.core, trailOf(f), f.defaultColor, null, f.defaultColor]);
    });
    ins.free();
  }

  function isWheelDb(d) {
    try {
      var t = d.exec("SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('feelings', 'notes')");
      return t.length && t[0].values.length === 2;
    } catch (e) { return false; }
  }

  // read added words, colors and notes out of the database into the page
  function loadFromDb() {
    var picks = {}, ns = {}, meta = {}, w = {};
    var r = sdb.exec("SELECT f.id, f.name, f.parent_id, f.added_at FROM feelings f WHERE f.ring = 'added'");
    if (r.length) r[0].values.forEach(function (row) {
      var parentKey = row[2] ? keyOfId(row[2]) : '';
      if (row[0] > 114 && row[1] && parentKey.indexOf('3:') === 0) {
        w[row[0]] = { id: row[0], name: String(row[1]), parent: +parentKey.slice(2), addedAt: row[3] || null };
      }
    });
    setWords(w);
    r = sdb.exec('SELECT id, chosen_color FROM feelings WHERE chosen_color IS NOT NULL AND chosen_color <> \'\'');
    if (r.length) r[0].values.forEach(function (row) {
      if (/^#[0-9a-fA-F]{6}$/.test(row[1])) picks[keyOfId(row[0])] = row[1].toLowerCase();
    });
    r = sdb.exec('SELECT feeling_id, text, updated_at FROM notes');
    if (r.length) r[0].values.forEach(function (row) {
      if (typeof row[1] === 'string' && row[1].trim()) {
        var key = keyOfId(row[0]);
        ns[key] = row[1];
        if (row[2]) meta[key] = row[2];
      }
    });
    state.picks = picks; notes = ns; notesMeta = meta;
    if (instance) {
      instance.clearAllPicks();
      Object.keys(picks).forEach(function (key) {
        var p = key.split(':'), c = rgb(picks[key]);
        instance.setPick(+p[0], +p[1], c[0], c[1], c[2]);
      });
      if (current) el.picker.value = String(instance.hexOf(current.level, current.idx)).toLowerCase();
    }
    applyNotesToSketch();
    refreshPanel();
    refreshNotesPanel();
  }

  function storeColors() {
    if (!sdb) return;
    sdb.run('UPDATE feelings SET chosen_color = NULL');
    Object.keys(state.picks).forEach(function (key) {
      sdb.run('UPDATE feelings SET chosen_color = ? WHERE id = ?', [state.picks[key], feelingId(key)]);
    });
    persistSoon();
  }

  function wordsReady() { return !!sdb; }
  function storeWord(w) {
    if (!sdb) return;
    var f = {
      level: 4, idx: w.id, key: '4:' + w.id, name: w.name,
      path: instance.pathOf(4, w.id)
    };
    sdb.run('INSERT OR REPLACE INTO feelings (' + COLUMNS + ', added_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
            [w.id, 'added', w.name, feelingId('3:' + w.parent), instance.nameOf(1, Math.floor(w.parent / 12)),
             trailOf(f), String(instance.defaultHexOf(4, w.id)).toLowerCase(), state.picks[f.key] || null,
             String(instance.hexOf(4, w.id)).toLowerCase(), w.addedAt]);
    persistSoon();
  }
  function unstoreWord(id) {
    if (!sdb) return;
    sdb.run('DELETE FROM notes WHERE feeling_id = ?', [id]);
    sdb.run('DELETE FROM feelings WHERE id = ?', [id]);
    persistSoon();
  }

  function storeNote(key, text) {
    if (text && text.trim()) {
      sdb.run('INSERT OR REPLACE INTO notes VALUES (?,?,?,?)',
              [feelingId(key), text, typedLines(text).join('\n'), notesMeta[key] || new Date().toISOString()]);
    } else {
      sdb.run('DELETE FROM notes WHERE feeling_id = ?', [feelingId(key)]);
    }
    persistSoon();
  }

  // the database as a file, with the colors the wheel is showing filled in
  function databaseBytes() {
    flushNote();
    if (instance) {
      var up = sdb.prepare('UPDATE feelings SET shown_color = ? WHERE id = ?');
      allFeelings().forEach(function (f) { up.run([f.shownColor, feelingId(f.key)]); });
      up.free();
    }
    metaSet('columns_per_line', String(noteBox.cols));
    metaSet('tab_size', String(noteBox.tabSize));
    metaSet('color_rule', 'A chosen color pulls the feeling one ring in 55%, two rings in 35% and three rings in 20% toward it; pulls combine as 1-(1-p1)(1-p2)...');
    return sdb.export();
  }

  function storeLabel() {
    if (linked && fileOk) return 'Saved to ' + linked.name;
    if (!browserOk) return 'Not saved in this browser. Save to a file or export to keep it.';
    return 'Saved in this browser';
  }

  function refreshStoreUi() {
    storeEl.state.textContent = !sdb ? 'Loading…'
      : linked ? (fileOk ? 'Saving in this browser and to ' + linked.name : 'Could not write to ' + linked.name + '. Saving in this browser only.')
      : (browserOk ? 'Saving in this browser' : 'This browser is not keeping your data. Save to a file or export to keep it.');
    storeEl.link.hidden = !canLink || !!linked || !sdb;
    storeEl.unlink.hidden = !linked;
    storeEl.open.disabled = !sdb;
    if (pendingKey === null && current) notesEl.status.textContent = savedLabel();
  }

  function persistSoon() {
    clearTimeout(persistTimer);
    persistTimer = setTimeout(persistNow, 400);
  }

  function persistNow() {
    clearTimeout(persistTimer);
    if (!sdb) return Promise.resolve();
    metaSet('saved_at', new Date().toISOString());
    var bytes = sdb.export();
    try { localStorage.setItem(DB_KEY, toB64(bytes)); browserOk = true; }
    catch (e) { browserOk = false; }
    var done = linked ? writeLinked(bytes) : Promise.resolve();
    return done.then(refreshStoreUi);
  }
  window.addEventListener('pagehide', function () { flushNote(); persistNow(); });

  function writeLinked(bytes) {
    var handle = linked;
    return handle.createWritable().then(function (w) {
      return w.write(bytes).then(function () { return w.close(); });
    }).then(function () { fileOk = true; }, function (e) {
      console.error('could not write the linked file', e);
      fileOk = false;
    });
  }

  // ---- remembering the linked file between visits (file handles live in IndexedDB) ----
  function idb(mode, fn) {
    return new Promise(function (resolve, reject) {
      var req;
      try { req = indexedDB.open('feelings-wheel', 1); } catch (e) { reject(e); return; }
      req.onupgradeneeded = function () { req.result.createObjectStore('kv'); };
      req.onerror = function () { reject(req.error); };
      req.onsuccess = function () {
        var tx = req.result.transaction('kv', mode), st = tx.objectStore('kv'), out = fn(st);
        tx.oncomplete = function () { resolve(out && out.result); };
        tx.onerror = function () { reject(tx.error); };
      };
    });
  }
  function rememberHandle(h) { return idb('readwrite', function (st) { return h ? st.put(h, 'file') : st.delete('file'); }).catch(function () {}); }
  function recallHandle() { return idb('readonly', function (st) { return st.get('file'); }).catch(function () { return null; }); }

  // linking: whichever copy was saved more recently wins, the other is brought up to date
  function linkTo(handle) {
    return handle.getFile().then(function (file) {
      return file.arrayBuffer();
    }).then(function (buf) {
      var bytes = new Uint8Array(buf), fileDb = null;
      if (bytes.length) { try { fileDb = new SQL.Database(bytes); } catch (e) { fileDb = null; } }
      linked = handle; fileOk = true;
      if (fileDb && isWheelDb(fileDb)) {
        var r = fileDb.exec("SELECT value FROM meta WHERE key = 'saved_at'");
        var fileAt = r.length ? r[0].values[0][0] : '';
        var ourAt = metaGet('saved_at') || '';
        if (fileAt > ourAt) {
          sdb.close(); sdb = fileDb; ensureFeelings(); loadFromDb();
          storeEl.msg.textContent = 'Loaded the newer copy from ' + handle.name + '.';
        } else { fileDb.close(); }
      } else if (fileDb) { fileDb.close(); }
      rememberHandle(handle);
      return persistNow();
    });
  }

  storeEl.link.addEventListener('click', function () {
    flushNote();
    window.showSaveFilePicker({
      suggestedName: 'feelings-wheel.sqlite',
      types: [{ description: 'SQLite database', accept: { 'application/vnd.sqlite3': ['.sqlite', '.db'] } }]
    }).then(function (handle) {
      linked = handle; fileOk = true;
      rememberHandle(handle);
      storeEl.msg.textContent = '';
      return persistNow();
    }).catch(function (e) {
      if (e && e.name === 'AbortError') return;
      storeEl.msg.textContent = 'Could not set up the file. Your data is still saved in this browser.';
    });
  });

  storeEl.reconnect.addEventListener('click', function () {
    var h = storeEl.reconnect._handle;
    if (!h) return;
    h.requestPermission({ mode: 'readwrite' }).then(function (p) {
      if (p !== 'granted') { storeEl.msg.textContent = 'Not reconnected. Your data is still saved in this browser.'; return; }
      storeEl.reconnect.hidden = true;
      return linkTo(h);
    }).catch(function () { storeEl.msg.textContent = 'Could not reach ' + h.name + '. It may have been moved or deleted.'; });
  });

  storeEl.unlink.addEventListener('click', function () {
    linked = null; fileOk = true;
    rememberHandle(null);
    storeEl.msg.textContent = 'The file stays where it is; it just won\'t be updated anymore.';
    refreshStoreUi();
  });

  // ---- opening a database file replaces what is in the page, after asking ----
  var pendingOpen = null;
  function askReplace(bytes, name, handle) {
    var d;
    try { d = new SQL.Database(bytes); } catch (e) { d = null; }
    if (!d || !isWheelDb(d)) {
      if (d) d.close();
      storeEl.msg.textContent = name + ' is not a feelings wheel database.';
      return;
    }
    pendingOpen = { db: d, name: name, handle: handle };
    var hasData = Object.keys(state.picks).length || Object.keys(notes).length;
    if (!hasData) { confirmOpen(); return; }
    storeEl.confirmText.textContent = 'Replace your current colors and notes with ' + name + '?';
    storeEl.confirm.hidden = false;
    storeEl.no.focus();
  }
  function confirmOpen() {
    var p = pendingOpen; pendingOpen = null;
    storeEl.confirm.hidden = true;
    if (!p) return;
    flushNote();
    sdb.close(); sdb = p.db; ensureFeelings(); loadFromDb();
    storeEl.msg.textContent = 'Opened ' + p.name + '.';
    // in browsers that can write files, keep saving to the file you opened
    if (p.handle && p.handle.requestPermission) {
      p.handle.requestPermission({ mode: 'readwrite' }).then(function (perm) {
        if (perm === 'granted') { linked = p.handle; fileOk = true; rememberHandle(p.handle); }
      }).catch(function () {}).then(persistNow);
    } else {
      linked = null; rememberHandle(null);
      persistNow();
    }
  }
  storeEl.yes.addEventListener('click', confirmOpen);
  storeEl.no.addEventListener('click', function () {
    if (pendingOpen) pendingOpen.db.close();
    pendingOpen = null; storeEl.confirm.hidden = true; storeEl.msg.textContent = '';
  });

  storeEl.open.addEventListener('click', function () {
    storeEl.msg.textContent = '';
    if (typeof window.showOpenFilePicker === 'function') {
      window.showOpenFilePicker({
        types: [{ description: 'SQLite database', accept: { 'application/vnd.sqlite3': ['.sqlite', '.sqlite3', '.db'] } }]
      }).then(function (hs) {
        var h = hs[0];
        return h.getFile().then(function (f) { return f.arrayBuffer(); }).then(function (buf) {
          askReplace(new Uint8Array(buf), h.name, h);
        });
      }).catch(function (e) {
        if (e && e.name === 'AbortError') return;
        storeEl.msg.textContent = 'Could not open that file.';
      });
    } else {
      storeEl.file.value = '';
      storeEl.file.click();
    }
  });
  storeEl.file.addEventListener('change', function () {
    var f = storeEl.file.files && storeEl.file.files[0];
    if (!f) return;
    f.arrayBuffer().then(function (buf) { askReplace(new Uint8Array(buf), f.name, null); })
      .catch(function () { storeEl.msg.textContent = 'Could not read that file.'; });
  });

  function whenInstance() {
    return new Promise(function (resolve) {
      (function wait() { if (instance) resolve(); else setTimeout(wait, 50); })();
    });
  }

  function initNotes() {
    whenInstance().then(function () {
      return window.initSqlJs();
    }).then(function (S) {
      SQL = S;
      var saved = null;
      try { saved = localStorage.getItem(DB_KEY); } catch (e) { browserOk = false; }
      if (saved) {
        try { sdb = new SQL.Database(fromB64(saved)); if (!isWheelDb(sdb)) { sdb.close(); sdb = null; } } catch (e) { sdb = null; }
      }
      if (!sdb) sdb = new SQL.Database();
      ensureFeelings();
      loadFromDb();
      refreshStoreUi();
      // a file linked on an earlier visit: reconnect now if the browser still allows it, otherwise offer a button
      if (!canLink) return;
      return recallHandle().then(function (h) {
        if (!h || !h.queryPermission) return;
        return h.queryPermission({ mode: 'readwrite' }).then(function (p) {
          if (p === 'granted') return linkTo(h);
          storeEl.reconnect._handle = h;
          storeEl.reconnect.textContent = 'Reconnect to ' + h.name;
          storeEl.reconnect.hidden = false;
        });
      });
    }).catch(function (e) {
      console.error('database failed to start', e);
      storeEl.state.textContent = 'The database could not start in this browser.';
    });
  }

''' + s[b:]

rep('''  function applyNotesToSketch() {''', '''  function applyNotesToSketch() {''')

# ---------------------------------------------------------------- SQLite export: the live database itself
a = s.index('  // builds a real SQLite file (sql.js, the pure-JavaScript build) and zips it')
b = s.index('  function refreshExportAll() {')
s = s[:a] + '''  function exportSqlite() {
    return Promise.resolve(new Blob([databaseBytes()], { type: 'application/vnd.sqlite3' }));
  }

''' + s[b:]
rep("else work = exportSqlite(list).then(function (blob) { return { name: 'feelings-wheel-' + stampName + '.zip', data: blob }; });",
    "else work = exportSqlite().then(function (blob) { return { name: 'feelings-wheel-' + stampName + '.sqlite', data: blob }; });")
rep("all.msg.textContent = kind === 'sqlite' ? 'Building the database…' : 'Preparing…';",
    "all.msg.textContent = 'Preparing…';")
rep('''  function refreshExportAll() {
    all.wrap.hidden = !downloads;
  }''', '''  function refreshExportAll() {}''')
rep("if (!downloads || !instance) return;\n    flushNote();\n    var list = allFeelings();",
    "if (!downloads || !instance || !sdb) return;\n    flushNote();\n    var list = allFeelings();")

# ---------------------------------------------------------------- a complete document
# Inside Claude the page is wrapped in a document for you. On its own (opened from disk or hosted,
# e.g. on GitHub Pages) it needs its own doctype, character set and mobile viewport, or browsers
# fall back to quirks mode and phones show it zoomed out at desktop width.
s = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
     '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
     '<style>:root { padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }\n'
     'body { margin: 0; font: 14px system-ui, -apple-system, "Segoe UI", sans-serif; }\n'
     'img { max-width: 100%; } [hidden] { display: none !important; }</style>\n'
     '</head>\n<body>\n' + s + '\n</body>\n</html>\n')

out = ROOT / 'dist' / 'feelings-wheel-standalone.html'
out.parent.mkdir(exist_ok=True)
out.write_text(s)
print('wrote', out, round(out.stat().st_size / 1024), 'KB')
