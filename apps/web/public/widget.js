(function() {
  var BASE = window.RAG_WIDGET_URL || 'https://rag.marinenationale.cloud';
  var TOKEN = window.RAG_WIDGET_TOKEN || '';

  var style = document.createElement('style');
  style.textContent = [
    '#rag-widget-btn { position:fixed; bottom:24px; right:24px; width:56px; height:56px; border-radius:50%; background:#2563eb; color:white; border:none; cursor:pointer; box-shadow:0 4px 12px rgba(37,99,235,0.3); z-index:9999; font-size:24px; display:flex; align-items:center; justify-content:center; transition:transform 0.2s; }',
    '#rag-widget-btn:hover { transform:scale(1.1); }',
    '#rag-widget-panel { position:fixed; bottom:96px; right:24px; width:380px; max-height:500px; background:white; border-radius:12px; box-shadow:0 8px 32px rgba(0,0,0,0.15); z-index:9999; display:none; flex-direction:column; overflow:hidden; font-family:Inter,system-ui,sans-serif; }',
    '#rag-widget-panel.open { display:flex; }',
    '#rag-widget-header { padding:12px 16px; background:#f5f5f4; border-bottom:1px solid #e7e5e4; font-size:14px; font-weight:600; color:#1c1917; }',
    '#rag-widget-messages { flex:1; overflow-y:auto; padding:12px; max-height:340px; }',
    '.rag-msg { margin-bottom:8px; font-size:13px; line-height:1.5; }',
    '.rag-msg.user { text-align:right; }',
    '.rag-msg .bubble { display:inline-block; max-width:85%; padding:8px 12px; border-radius:12px; }',
    '.rag-msg.user .bubble { background:#2563eb; color:white; border-bottom-right-radius:4px; }',
    '.rag-msg.assistant .bubble { background:#f5f5f4; color:#1c1917; border-bottom-left-radius:4px; }',
    '#rag-widget-input { display:flex; gap:8px; padding:8px 12px; border-top:1px solid #e7e5e4; }',
    '#rag-widget-input input { flex:1; border:1px solid #d6d3d1; border-radius:8px; padding:8px 12px; font-size:13px; outline:none; }',
    '#rag-widget-input input:focus { border-color:#2563eb; }',
    '#rag-widget-input button { background:#2563eb; color:white; border:none; border-radius:8px; padding:8px 16px; cursor:pointer; font-size:13px; }',
  ].join('\n');
  document.head.appendChild(style);

  var btn = document.createElement('button');
  btn.id = 'rag-widget-btn';
  btn.innerHTML = '\uD83D\uDCAC';
  document.body.appendChild(btn);

  var panel = document.createElement('div');
  panel.id = 'rag-widget-panel';
  panel.innerHTML = '<div id="rag-widget-header">\uD83D\uDCC4 Assistant documentaire</div><div id="rag-widget-messages"></div><div id="rag-widget-input"><input placeholder="Posez votre question..." /><button>Envoyer</button></div>';
  document.body.appendChild(panel);

  btn.onclick = function() { panel.classList.toggle('open'); };

  var input = panel.querySelector('input');
  var sendBtn = panel.querySelector('#rag-widget-input button');
  var msgs = panel.querySelector('#rag-widget-messages');

  function addMsg(role, text) {
    var div = document.createElement('div');
    div.className = 'rag-msg ' + role;
    div.innerHTML = '<span class="bubble">' + text.replace(/\n/g, '<br>') + '</span>';
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  async function send() {
    var q = input.value.trim();
    if (!q) return;
    addMsg('user', q);
    input.value = '';
    try {
      var res = await fetch(BASE + '/api/chat/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOKEN },
        body: JSON.stringify({ query: q }),
      });
      var data = await res.json();
      addMsg('assistant', data.answer || data.detail || 'Erreur');
    } catch(e) {
      addMsg('assistant', 'Erreur de connexion');
    }
  }

  sendBtn.onclick = send;
  input.onkeydown = function(e) { if (e.key === 'Enter') send(); };
})();
