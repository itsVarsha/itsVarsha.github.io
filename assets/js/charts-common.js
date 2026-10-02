/* Shared chart settings and helpers for the solution showcase pages. Uses Chart.js (MIT), served from assets/vendor. */
(function () {
  var VS = window.VS = {
    palette: ['#1B365D', '#2A9D8F', '#E9C46A', '#B5403A', '#6C8EBF', '#8AB17D', '#F4A261', '#7B6D8D'],
    aed: function (v) { return 'AED ' + Math.round(v).toLocaleString('en-US'); },
    aedShort: function (v) {
      var a = Math.abs(v), s = v < 0 ? '-' : '';
      if (a >= 1e6) return s + 'AED ' + (a / 1e6).toFixed(2) + 'M';
      if (a >= 1e3) return s + 'AED ' + (a / 1e3).toFixed(0) + 'K';
      return s + 'AED ' + Math.round(a);
    },
    num: function (v) { return Number(v).toLocaleString('en-US'); },
    esc: function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); },
    table: function (el, head, rows, numCols) {
      numCols = numCols || [];
      var h = '<table class="data"><thead><tr>' + head.map(function (t, i) { return '<th' + (numCols.indexOf(i) > -1 ? ' class="num"' : '') + ' scope="col">' + t + '</th>'; }).join('') + '</tr></thead><tbody>';
      h += rows.map(function (r) { return '<tr>' + r.map(function (c, i) { return '<td' + (numCols.indexOf(i) > -1 ? ' class="num"' : '') + '>' + c + '</td>'; }).join('') + '</tr>'; }).join('');
      el.innerHTML = h + '</tbody></table>';
    },
    seg: function (container, onChange) {
      var btns = container.querySelectorAll('button');
      btns.forEach(function (b) {
        b.addEventListener('click', function () {
          btns.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
          onChange(b.dataset.value);
        });
      });
    }
  };
  if (!window.Chart) return;
  var C = Chart.defaults;
  C.font.family = '"Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif';
  C.font.size = 12;
  C.color = '#4B5563';
  C.borderColor = '#E5E9EF';
  C.maintainAspectRatio = false;
  C.plugins.legend.labels.boxWidth = 12;
  C.plugins.legend.labels.boxHeight = 12;
  C.plugins.tooltip.backgroundColor = '#1B365D';
  C.animation.duration = 400;
  VS.moneyAxis = { ticks: { callback: function (v) { return VS.aedShort(v); } } };
  VS.moneyTip = { callbacks: { label: function (c) { return ' ' + c.dataset.label + ': ' + VS.aed(c.parsed.y !== undefined && c.chart.options.indexAxis !== 'y' ? c.parsed.y : c.parsed.x); } } };
})();
