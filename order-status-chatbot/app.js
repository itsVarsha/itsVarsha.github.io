(function () {
  var D = window.PROJECT_DATA, VS = window.VS, P = VS.palette;
  var colors = { 'Delivered': P[1], 'Out for delivery': P[0], 'Packed': P[4], 'Picking': P[2], 'Received': '#9AA5B1', 'On hold, credit check': P[3], 'Cancelled': '#5B6573' };
  new Chart(document.getElementById('c-status'), {
    type: 'doughnut', data: { labels: D.status.labels, datasets: [{ data: D.status.values, backgroundColor: D.status.labels.map(function (l) { return colors[l]; }), borderWidth: 1 }] },
    options: { cutout: '58%', plugins: { legend: { position: 'right' } } }
  });
  var st = Object.keys(D.daily.series);
  new Chart(document.getElementById('c-daily'), {
    type: 'bar', data: { labels: D.daily.labels, datasets: st.map(function (s) { return { label: s, data: D.daily.series[s], backgroundColor: colors[s] }; }) },
    options: { scales: { x: { stacked: true, ticks: { maxTicksLimit: 10 } }, y: { stacked: true, title: { display: true, text: 'Orders' } } }, plugins: { legend: { position: 'bottom' } } }
  });
  new Chart(document.getElementById('c-emirate'), {
    type: 'bar', data: { labels: D.emirate.labels, datasets: [{ label: 'On-time delivery %', data: D.emirate.on_time, backgroundColor: D.emirate.on_time.map(function (v) { return v < 92 ? P[3] : P[1]; }) }] },
    options: { indexAxis: 'y', scales: { x: { min: 80, max: 100, ticks: { callback: function (v) { return v + '%'; } } } },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (c) { return ' ' + c.parsed.x.toFixed(1) + '% on time (' + VS.num(D.emirate.orders[c.dataIndex]) + ' deliveries)'; } } } } }
  });
})();
