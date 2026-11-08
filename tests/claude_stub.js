// A stand-in for the features the page gets when it runs inside Claude (window.claude.use).
// Injected before the page loads by tests/conftest.py, only for the Claude version (src/feelings-wheel.html).
//
//   db         an in-memory document store: collection(path).doc(id).set/delete, onSnapshot
//   user       a fixed user id
//   downloads  save({filename, data}) records the file in window.__saved instead of saving it
//
// Tests read window.__store (documents by id) and window.__saved ({name, text} or {name, dataUrl}).
(function () {
  var store = {};
  var listeners = [];
  window.__store = store;
  window.__saved = null;
  window.__savedAll = [];

  function snapshot() {
    return {
      docs: Object.keys(store).map(function (id) {
        return { id: id, exists: true, data: function () { return store[id]; } };
      })
    };
  }
  function notify() { setTimeout(function () { listeners.forEach(function (fn) { fn(snapshot()); }); }, 5); }

  var collection = {
    doc: function (id) {
      return {
        set: function (data) { store[id] = JSON.parse(JSON.stringify(data)); notify(); return Promise.resolve(); },
        delete: function () { delete store[id]; notify(); return Promise.resolve(); }
      };
    },
    onSnapshot: function (fn) {
      listeners.push(fn);
      setTimeout(function () { fn(snapshot()); }, 20);
      return function () { listeners = listeners.filter(function (f) { return f !== fn; }); };
    }
  };

  var capabilities = {
    db: { collection: function (path) { window.__dbPath = path; return collection; } },
    user: { id: function () { return Promise.resolve('test-user'); } },
    downloads: {
      save: function (req) {
        return new Promise(function (resolve) {
          function done(entry) { window.__saved = entry; window.__savedAll.push(entry); resolve({ status: 'saved' }); }
          if (typeof req.data === 'string') { done({ name: req.filename, text: req.data }); return; }
          var reader = new FileReader();
          reader.onload = function () { done({ name: req.filename, dataUrl: reader.result }); };
          reader.readAsDataURL(req.data instanceof Blob ? req.data : new Blob([req.data]));
        });
      }
    }
  };

  window.claude = { use: function (name) { return Promise.resolve(capabilities[name] || null); } };
})();
