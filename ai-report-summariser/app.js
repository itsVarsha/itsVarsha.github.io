(function () {
  var D = window.PROJECT_DATA, VS = window.VS, P = VS.palette;
  var chart = new Chart(document.getElementById('c-trend'), {
    data: { labels: D.chart.labels, datasets: [
      { type: 'bar', label: 'Net sales', data: D.chart.net, backgroundColor: D.chart.labels.map(function () { return '#BFD3E6'; }), yAxisID: 'y' },
      { type: 'line', label: 'Gross margin %', data: D.chart.gm, borderColor: P[1], backgroundColor: P[1], tension: .3, yAxisID: 'y2', pointRadius: 3 }] },
    options: { interaction: { mode: 'index', intersect: false },
      scales: { y: VS.moneyAxis, y2: { position: 'right', grid: { drawOnChartArea: false }, ticks: { callback: function (v) { return v.toFixed(1) + '%'; } } } },
      plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { label: function (c) { return ' ' + c.dataset.label + ': ' + (c.dataset.yAxisID === 'y2' ? c.parsed.y.toFixed(1) + '%' : VS.aed(c.parsed.y)); } } } } }
  });
  function card(n) {
    var h = '<h3>' + VS.esc(n.month) + '</h3><p>' + VS.esc(n.summary) + '</p>';
    if (n.watch.length) h += '<div class="watch"><strong>Watch list</strong><ul>' + n.watch.map(function (w) { return '<li>' + VS.esc(w) + '</li>'; }).join('') + '</ul></div>';
    h += '<p class="kline">Inputs: net sales ' + VS.aed(n.kpis.net_sales) + ', gross margin ' + n.kpis.gm_pct + '%, DSO ' + n.kpis.dso + ' days, overdue ' + n.kpis.overdue_pct + '%, month-end cash ' + VS.aed(n.kpis.cash) + '. Rules fired: ' + n.rules_fired + '.</p>';
    return h;
  }
  var sel = document.getElementById('month-select'), out = document.getElementById('narr-out');
  D.narratives.forEach(function (n, i) { var o = document.createElement('option'); o.value = i; o.textContent = n.month; sel.appendChild(o); });
  function show(i) {
    out.innerHTML = card(D.narratives[i]);
    var lbl = D.chart.labels.length - D.narratives.length + Number(i);
    chart.data.datasets[0].backgroundColor = D.chart.labels.map(function (_, j) { return j === lbl ? P[0] : '#BFD3E6'; });
    chart.update();
  }
  sel.addEventListener('change', function () { show(sel.value); });
  sel.value = D.narratives.length - 1; show(sel.value);
  document.querySelectorAll('[data-example]').forEach(function (el) {
    var n = D.narratives.filter(function (x) { return x.key === el.dataset.example; })[0];
    if (n) el.innerHTML = card(n);
  });
})();
