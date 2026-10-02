(function () {
  var D = window.PROJECT_DATA, VS = window.VS, P = VS.palette;
  var br = Object.keys(D.ageing.series);
  new Chart(document.getElementById('c-ageing'), {
    type: 'bar', data: { labels: D.ageing.labels, datasets: br.map(function (b, i) { return { label: b, data: D.ageing.series[b], backgroundColor: [P[0], P[1], P[2]][i] }; }) },
    options: { scales: { x: { stacked: true }, y: Object.assign({ stacked: true }, VS.moneyAxis) }, plugins: { tooltip: VS.moneyTip, legend: { position: 'bottom' } } }
  });
  new Chart(document.getElementById('c-dso'), {
    data: { labels: D.dso.labels, datasets: [
      { type: 'line', label: 'DSO (days)', data: D.dso.dso, borderColor: P[3], backgroundColor: P[3], tension: .3, yAxisID: 'y', pointRadius: 3 },
      { type: 'line', label: 'Average credit terms (days)', data: D.dso.labels.map(function () { return D.dso.terms; }), borderColor: '#9AA5B1', borderDash: [6, 4], pointRadius: 0, yAxisID: 'y' },
      { type: 'bar', label: 'Open receivables (AED)', data: D.dso.ar, backgroundColor: '#D5E1EC', yAxisID: 'y2' }] },
    options: { interaction: { mode: 'index', intersect: false },
      scales: { y: { position: 'left', title: { display: true, text: 'Days' }, suggestedMin: 40 }, y2: Object.assign({ position: 'right', grid: { drawOnChartArea: false } }, VS.moneyAxis) },
      plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { label: function (c) { return ' ' + c.dataset.label + ': ' + (c.dataset.yAxisID === 'y2' ? VS.aed(c.parsed.y) : c.parsed.y.toFixed(1)); } } } } }
  });
  var cashChart = new Chart(document.getElementById('c-cash'), {
    data: { labels: D.cash.labels, datasets: [
      { type: 'bar', label: 'Cash in', data: D.cash.cash_in, backgroundColor: P[1] },
      { type: 'bar', label: 'Cash out', data: D.cash.cash_out.map(function (v) { return -v; }), backgroundColor: '#D98C86' },
      { type: 'line', label: 'Closing balance', data: D.cash.closing, borderColor: P[0], backgroundColor: P[0], tension: .25, pointRadius: 2 }] },
    options: { interaction: { mode: 'index', intersect: false }, scales: { y: VS.moneyAxis }, plugins: { tooltip: VS.moneyTip, legend: { position: 'bottom' } } }
  });
  var outCats = Object.keys(D.cash.out_categories);
  var mixSets = outCats.map(function (k, i) { return { type: 'bar', label: k, data: D.cash.out_categories[k], backgroundColor: P[(i + 1) % P.length], stack: 'o' }; });
  var flowSets = cashChart.data.datasets;
  VS.seg(document.getElementById('seg-cash'), function (v) {
    cashChart.data.datasets = v === 'mix' ? mixSets : flowSets;
    cashChart.options.scales.x = { stacked: v === 'mix' }; cashChart.options.scales.y.stacked = v === 'mix';
    cashChart.update();
  });
  new Chart(document.getElementById('c-expected'), {
    type: 'bar', data: { labels: D.expected.labels, datasets: [{ label: 'Expected collections', data: D.expected.values, backgroundColor: P[1] }] },
    options: { scales: { y: VS.moneyAxis, x: { ticks: { maxRotation: 0, autoSkip: true } } }, plugins: { tooltip: VS.moneyTip, legend: { display: false } } }
  });
  var only = document.getElementById('only-limit'), wrap = document.getElementById('t-priority');
  function draw() {
    var rows = D.priority.filter(function (r) { return !only.checked || r[5]; }).map(function (r, i) {
      var cls = r[3] > 90 ? 'red' : r[5] ? 'red' : r[3] > 30 ? 'amber' : 'green';
      return [i + 1, VS.esc(r[0]), r[1], VS.aed(r[2]), r[3], r[4] === null ? 'n/a' : r[4].toFixed(0), r[5] ? 'Yes' : 'No', '<span class="pill ' + cls + '">' + r[6] + '</span>'];
    });
    VS.table(wrap, ['#', 'Customer', 'Salesperson', 'Overdue', 'Oldest overdue (days)', 'Avg days late, 12 months', 'Over credit limit', 'Suggested action'], rows, [3, 4, 5]);
  }
  only.addEventListener('change', draw); draw();
})();
