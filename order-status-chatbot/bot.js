/* Order-status chatbot: plain JavaScript, runs fully in the browser, no external services. */
(function () {
  var VS = window.VS, log = document.getElementById('chat-log'), form = document.getElementById('chat-form'), input = document.getElementById('chat-input');
  var DB = null, byId = {}, asOf = null;
  var DAY = 86400000;
  function d(off) { if (off === null || off === undefined) return null; return new Date(asOf.getTime() + off * DAY); }
  function fmt(dt) { return dt.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }); }
  function say(text, who) {
    var m = document.createElement('div'); m.className = 'msg ' + (who || 'bot'); m.textContent = text;
    log.appendChild(m); log.scrollTop = log.scrollHeight; return m;
  }
  var FAQ = [
    { k: /\b(hi|hello|hey|salam|assalam|good (morning|afternoon|evening))\b/, a: 'Hello! I can check an order status, or answer questions about delivery, payments, returns and opening hours. To track an order, type its number, for example TW-78537.' },
    { k: /\b(thank|thanks|shukran)\b/, a: 'You are welcome. Anything else I can check for you?' },
    { k: /\b(human|person|agent|someone|speak|call me|talk to)\b/, a: 'I will pass this to the customer service team. In a live setup this creates a ticket and a team member replies here during working hours (Saturday to Thursday, 8 am to 6 pm). (No message is sent in this showcase.)' },
    { k: /\b(cancel|cancellation)\b/, a: 'Orders can be cancelled until they are packed. Send the order number with the word cancel, for example "cancel TW-78578", and I will check whether it is still possible. (No changes are made in this showcase.)' },
    { k: /\b(return|damaged|broken|missing|wrong item|refund|expired|credit note)\b/, a: 'Sorry about that. Please share the order number and a photo of the item within 48 hours of delivery. The team checks it and issues a replacement or a credit note on your account.' },
    { k: /\b(pay|payment|card|cash|cheque|check|bank transfer|transfer)\b/, a: 'Account customers pay by bank transfer or cheque within their credit terms. Cash and card are accepted on delivery for cash accounts. For your balance or a statement, ask "statement".' },
    { k: /\b(statement|balance|invoice copy|copy of invoice|soa|outstanding)\b/, a: 'I can send a statement of account to the email we have on file. In a live setup I would first confirm your account number and registered mobile, then Power Automate emails the PDF from the accounting system.' },
    { k: /\b(hours|open|opening|timing|timings|closed|friday|weekend)\b/, a: 'Customer service and the depots work Saturday to Thursday, 8 am to 6 pm. Friday deliveries run in the morning only.' },
    { k: /\b(minimum|min order|moq)\b/, a: 'A minimum order value applies to free delivery and depends on your area. Your salesperson can confirm the exact amount for your account.' },
    { k: /\b(deliver|delivery|shipping|ship|how long|when will|areas|emirate|emirates)\b/, a: 'We deliver across the UAE from three depots. Orders placed before 2 pm usually arrive the next working day in areas near a depot; other areas usually take 1 to 3 working days. To check a specific order, type its number.' },
    { k: /\b(track|tracking|status|where is|where's|my order|order)\b/, a: 'Sure. Please type the order number. It starts with TW, for example TW-78537, and is printed on your order confirmation and delivery note.' }
  ];
  function orderReply(id, wantsCancel) {
    var r = byId[id];
    if (!r) return 'I could not find order ' + id + '. Please check the number on your confirmation or delivery note. If it is a very new order it may take a few minutes to appear.';
    var c = DB.customers[r[5]], st = r[4], ordered = d(r[1]), prom = d(r[2]), del = d(r[3]);
    var head = 'Order ' + r[0] + ' for ' + c[0] + ' (' + c[1] + ')\nPlaced ' + fmt(ordered) + ', ' + r[8] + (r[8] === 1 ? ' item line, ' : ' item lines, ') + VS.aed(r[7]) + ' incl. VAT, from ' + r[6] + '.\n';
    var body;
    if (st === 'Delivered') {
      var late = Math.round((del - prom) / DAY);
      body = 'Status: delivered on ' + fmt(del) + (late > 0 ? ', ' + late + ' day' + (late > 1 ? 's' : '') + ' after the promised date of ' + fmt(prom) + '. Sorry for the delay.' : ', on time.');
    } else if (st === 'Out for delivery') body = 'Status: out for delivery today. It was promised for ' + fmt(prom) + '. The driver calls ahead before arriving.';
    else if (st === 'Packed') body = 'Status: packed and waiting for dispatch. Expected delivery: ' + fmt(prom) + '.';
    else if (st === 'Picking') body = 'Status: being picked in the warehouse. Expected delivery: ' + fmt(prom) + '.';
    else if (st === 'Received') body = 'Status: received and queued for picking. Expected delivery: ' + fmt(prom) + '.';
    else if (st.indexOf('On hold') === 0) body = 'Status: on hold pending a credit check on the account. The accounts team will contact you. You can also type "talk to a person".';
    else if (st === 'Cancelled') body = 'Status: cancelled. If you did not expect this, type "talk to a person" and the team will look into it.';
    else body = 'Status: ' + st + '.';
    if (wantsCancel) {
      body += ['Received', 'Picking'].indexOf(st) > -1 ? '\nThis order can still be cancelled. In a live setup I would ask you to confirm, then update the order system. (No changes are made in this showcase.)'
        : '\nThis order can no longer be cancelled at this stage. For help, type "talk to a person".';
    }
    return head + body;
  }
  function answer(text) {
    var t = text.toLowerCase();
    var m = t.match(/\btw[\s-]?(\d{4,6})\b/) || t.match(/(?:^|\D)(\d{5})(?:\D|$)/);
    if (m) return orderReply('TW-' + m[1], /\bcancel/.test(t));
    if (!DB) return 'Order data is still loading. Please try again in a moment.';
    for (var i = 0; i < FAQ.length; i++) if (FAQ[i].k.test(t)) return FAQ[i].a;
    return 'I did not quite get that. I can help with:\n- order status (type an order number such as TW-78537)\n- delivery times and areas\n- payments and statements\n- returns and damaged items\n- opening hours\nor type "talk to a person".';
  }
  function ask(text) {
    if (!text.trim()) return;
    say(text, 'user');
    var reply = answer(text);
    setTimeout(function () { say(reply, 'bot'); }, 250);
  }
  form.addEventListener('submit', function (e) { e.preventDefault(); ask(input.value); input.value = ''; input.focus(); });
  document.querySelectorAll('[data-ask]').forEach(function (b) { b.addEventListener('click', function () { ask(b.dataset.ask); }); });
  say('Hi, I am the Tidewell order assistant. Type an order number to track it, or ask about delivery, payments, returns or opening hours.');
  fetch('orders.json').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (j) {
    DB = j; asOf = new Date(j.asOf + 'T00:00:00Z');
    j.orders.forEach(function (r) { byId[r[0]] = r; });
    document.getElementById('bot-status').textContent = VS.num(j.orders.length) + ' orders loaded';
    window.BOT_READY = true;
  }).catch(function () {
    say('Order data could not be loaded. If you opened this page straight from disk, run a local web server or view it on the published site.');
  });
  window.botAnswer = answer;
})();
