
(function () {
  window.__stubRan = (window.__stubRan || 0) + 1;
  try {
    var orig = (window.CSS && CSS.supports) ? CSS.supports.bind(CSS) : null;
    window.CSS.supports = function (a, b) {
      if (typeof a === 'string' && a.indexOf('selector(') === 0) { return false; }
      return orig ? orig(a, b) : false;
    };
  } catch (e) { window.__stubErr = String(e); }
})();
