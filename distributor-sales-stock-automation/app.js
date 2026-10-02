(function () {
  var D = window.PROJECT_DATA, VS = window.VS, P = VS.palette;
  // daily sales with 7-day average
  new Chart(document.getElementById('c-daily'), {
    data: { labels: D.daily.labels, datasets: [
      { type: 'bar', label: 'Net sales', data: D.daily.sales, backgroundColor: '#BFD3E6', borderRadius: 2, order: 2 },
      { type: 'line', label: '7-day average', data: D.daily.ma7, borderColor: P[0], borderWidth: 2, pointRadius: 0, tension: .3, order: 1 }] },
    options: { interaction: { mode: 'index', intersect: false }, scales: { x: { ticks: { maxTicksLimit: 10 } }, y: VS.moneyAxis }, plugins: { tooltip: VS.moneyTip } }
  });
  // monthly sales by category, switchable
  var cats = Object.keys(D.monthly.series);
  var total = D.monthly.labels.map(function (_, i) { return cats.reduce(function (s, c) { return s + D.monthly.series[c][i]; }, 0); });
  var catSets = cats.map(function (c, i) { return { label: c, data: D.monthly.series[c], backgroundColor: P[i % P.length], stack: 's' }; });
  var totSets = [{ label: 'Total net sales', data: total, backgroundColor: P[0] }];
  var mChart = new Chart(document.getElementById('c-monthly'), {
    type: 'bar', data: { labels: D.monthly.labels, datasets: catSets },
    options: { scales: { x: { stacked: true }, y: Object.assign({ stacked: true }, VS.moneyAxis) }, plugins: { tooltip: VS.moneyTip, legend: { position: 'bottom' } } }
  });
  VS.seg(document.getElementById('seg-monthly'), function (v) {
    mChart.data.datasets = v === 'total' ? totSets : catSets; mChart.update();
  });
  // stock ageing by branch
  var br = Object.keys(D.ageing.series);
  new Chart(document.getElementById('c-ageing'), {
    type: 'bar', data: { labels: D.ageing.labels, datasets: br.map(function (b, i) { return { label: b, data: D.ageing.series[b], backgroundColor: [P[0], P[1], P[2]][i] }; }) },
    options: { scales: { x: { stacked: true }, y: Object.assign({ stacked: true }, VS.moneyAxis) }, plugins: { tooltip: VS.moneyTip, legend: { position: 'bottom' } } }
  });
  // reorder alert table with branch filter
  var sel = document.getElementById('alert-branch'), wrap = document.getElementById('t-alerts');
  function drawAlerts() {
    var rows = D.alerts.filter(function (r) { return sel.value === 'all' || r[1] === sel.value; }).map(function (r) {
      return [VS.esc(r[0]), r[1], VS.num(r[2]), VS.num(r[3]), VS.num(r[4]), r[5] === null ? 'n/a' : r[5].toFixed(1), VS.num(r[6]),
        '<span class="pill ' + (r[7] === 'Reorder now' ? 'amber' : 'red') + '">' + r[7] + '</span>'];
    });
    if (!rows.length) rows = [['No alerts for this branch in the top 15', '', '', '', '', '', '', '']];
    VS.table(wrap, ['Item', 'Branch', 'On hand', 'On order', 'Reorder level', 'Days of cover', 'Suggested order', 'Status'], rows, [2, 3, 4, 5, 6]);
  }
  sel.addEventListener('change', drawAlerts); drawAlerts();
  VS.table(document.getElementById('t-slow'), ['Item', 'Branch', 'Qty', 'Value at cost', 'Oldest (days)', 'Sold, last 90 days'],
    D.slow.map(function (r) { return [VS.esc(r[0]), r[1], VS.num(r[2]), VS.aed(r[3]), r[4], VS.num(r[5])]; }), [2, 3, 4, 5]);
})();
