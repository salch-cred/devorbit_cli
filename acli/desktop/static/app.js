/* DevOrbit Desktop — Application Logic */
(function() {
'use strict';

// ─── State ────────────────────────────────────────────────────────────
let ws = null;
let currentView = 'chat';
let settingsData = null;
let settingsSections = ['account','permissions','appearance','models','customizations','browser','app','conversations'];
let settingsFields = {
  account: [
    {key:'telemetry', label:'Enable telemetry', type:'bool'},
    {key:'marketing_emails', label:'Marketing emails', type:'bool'},
    {key:'display_email', label:'Display email', type:'str'},
    {key:'plan_label', label:'Plan label', type:'str'},
  ],
  permissions: [
    {key:'auto_approve', label:'Auto-approve mutating actions', type:'bool'},
    {key:'workspace_dir', label:'Workspace directory', type:'str'},
    {key:'allow_file_reads', label:'Allow file reads', type:'bool'},
    {key:'allow_file_writes', label:'Allow file writes/edits', type:'bool'},
    {key:'denied_file_patterns', label:'Denied file patterns', type:'list'},
    {key:'network_default', label:'Network default (allow/deny)', type:'str'},
    {key:'allowed_domains', label:'Allowed network domains', type:'list'},
    {key:'denied_domains', label:'Denied network domains', type:'list'},
    {key:'terminal_policy', label:'Terminal policy', type:'str'},
    {key:'sandbox_backend', label:'Sandbox backend', type:'str'},
    {key:'allow_native_terminal', label:'Allow native terminal fallback', type:'bool'},
    {key:'allow_outside_workspace', label:'Commands outside workspace', type:'bool'},
    {key:'mcp_tools_enabled', label:'MCP tools enabled', type:'bool'},
  ],
  appearance: [
    {key:'verbose_agent_chat', label:'Verbose agent steps', type:'bool'},
    {key:'conversation_width', label:'Conversation width', type:'str'},
    {key:'theme', label:'Theme (dark/light/system)', type:'str'},
    {key:'light_background', label:'Light background', type:'str'},
    {key:'light_foreground', label:'Light foreground', type:'str'},
    {key:'light_accent', label:'Light accent', type:'str'},
    {key:'dark_background', label:'Dark background', type:'str'},
    {key:'dark_foreground', label:'Dark foreground', type:'str'},
    {key:'dark_accent', label:'Dark accent', type:'str'},
  ],
  models: [
    {key:'provider', label:'AI provider', type:'str'},
    {key:'primary_model', label:'Primary model', type:'str'},
    {key:'auto_route', label:'Automatic task routing', type:'bool'},
    {key:'response_cache', label:'Response cache', type:'bool'},
    {key:'temperature', label:'Temperature', type:'float'},
    {key:'context_tokens', label:'Context token budget', type:'int'},
    {key:'retries_per_model', label:'Retries per model', type:'int'},
    {key:'backoff_seconds', label:'Retry backoff seconds', type:'float'},
    {key:'max_tool_iterations', label:'Maximum tool iterations', type:'int'},
  ],
  customizations: [
    {key:'system_prompt', label:'Custom system prompt', type:'str'},
    {key:'enabled_skills', label:'Enabled skills', type:'list'},
    {key:'mcp_servers', label:'Installed MCP server commands', type:'list'},
    {key:'custom_rules', label:'Custom agent rules', type:'list'},
  ],
  browser: [
    {key:'headless', label:'Headless browser', type:'bool'},
    {key:'javascript_policy', label:'JavaScript policy (ask/allow/deny)', type:'str'},
    {key:'confirm_actuation', label:'Confirm clicks/typing/keys', type:'bool'},
    {key:'allowed_domains', label:'Allowed actuation domains', type:'list'},
    {key:'denied_domains', label:'Denied actuation domains', type:'list'},
    {key:'download_dir', label:'Download/screenshot directory', type:'str'},
  ],
  app: [
    {key:'prevent_sleep', label:'Prevent sleep while running', type:'bool'},
    {key:'keep_in_background', label:'Keep process in background', type:'bool'},
    {key:'notifications', label:'Terminal notifications', type:'bool'},
    {key:'check_updates', label:'Check for updates', type:'bool'},
  ],
  conversations: [
    {key:'autosave', label:'Autosave conversations', type:'bool'},
    {key:'history_dir', label:'Conversation history directory', type:'str'},
    {key:'max_saved', label:'Maximum saved conversations', type:'int'},
    {key:'save_tool_results', label:'Save tool results', type:'bool'},
  ],
};

// ─── API helpers ──────────────────────────────────────────────────────
async function api(path, method='GET', body=null) {
  const opts = {method, headers: {'Content-Type':'application/json'}};
  if (body) opts.body = JSON.stringify(body);
  const resp = await fetch('/api/' + path, opts);
  return resp.json();
}

// ─── WebSocket ────────────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(proto + '://' + location.host + '/ws/chat');

  ws.onopen = () => {
    document.querySelector('.status-dot').className = 'status-dot connected';
    document.querySelector('.status-text').textContent = 'Connected';
  };

  ws.onclose = () => {
    document.querySelector('.status-dot').className = 'status-dot error';
    document.querySelector('.status-text').textContent = 'Disconnected';
    setTimeout(connectWS, 2000);
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleWSMessage(data);
  };
}

function handleWSMessage(data) {
  const container = document.getElementById('chatMessages');

  switch(data.type) {
    case 'response':
      addMessage('assistant', data.content);
      break;
    case 'system':
      addMessage('system', data.message);
      break;
    case 'status':
      addMessage('status', data.message);
      break;
    case 'error':
      addMessage('error', data.message);
      break;
    case 'confirm':
      showConfirmModal(data.id, data.description);
      break;
  }
  container.scrollTop = container.scrollHeight;
}

function sendWS(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  }
}

// ─── Chat ─────────────────────────────────────────────────────────────
function addMessage(role, content) {
  const container = document.getElementById('chatMessages');
  // Remove welcome message
  const welcome = container.querySelector('.welcome-msg');
  if (welcome) welcome.remove();

  // Remove last status message
  if (role === 'status' || role === 'system') {
    const lastStatus = container.querySelector('.msg.status:last-child');
    if (lastStatus) lastStatus.remove();
  }

  const div = document.createElement('div');
  div.className = 'msg ' + role;

  // Format code blocks
  let formatted = content;
  if (role === 'assistant' || role === 'system') {
    formatted = formatCodeBlocks(content);
  }
  div.innerHTML = formatted;

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function formatCodeBlocks(text) {
  // Replace ```code``` with <pre> blocks
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre>$2</pre>')
    .replace(/`([^`]+)`/g, '<code style="font-family:var(--mono);background:var(--bg-tertiary);padding:1px 4px;border-radius:3px;font-size:12px">$1</code>');
}

function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  addMessage('user', text);
  sendWS({type: 'message', content: text});
  input.value = '';
  input.style.height = 'auto';
}

// ─── Navigation ───────────────────────────────────────────────────────
function switchView(view) {
  currentView = view;
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + view).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector(`.nav-item[data-view="${view}"]`).classList.add('active');

  if (view === 'dashboard') loadDashboard();
  if (view === 'files') loadFiles();
  if (view === 'models') loadModels();
  if (view === 'tools') loadTools();
  if (view === 'settings') loadSettings();
}

// ─── Dashboard ────────────────────────────────────────────────────────
async function loadDashboard() {
  const data = await api('dashboard');
  const grid = document.getElementById('dashGrid');
  const cards = [
    {label:'Provider', value:data.provider, sub:'Active AI provider'},
    {label:'Primary Model', value:data.primary_model, sub:'First in fallback chain'},
    {label:'Last Model', value:data.last_model, sub:'Most recently used'},
    {label:'Workspace', value:data.workspace, sub:'File operations root'},
    {label:'Browser', value:data.browser, sub:'Playwright Chromium'},
    {label:'Tools Enabled', value:data.tools, sub:'Agent tool loop'},
    {label:'Auto Approve', value:data.auto_approve, sub:'Mutating actions'},
    {label:'Messages', value:data.messages, sub:'In conversation'},
    {label:'Models Available', value:data.models, sub:'In fallback chain'},
    {label:'Max Tool Loops', value:data.max_tool_loops, sub:'Per response'},
    {label:'Context Budget', value:data.context_budget, sub:'Tokens'},
    {label:'Temperature', value:data.temperature, sub:'Sampling temp'},
  ];
  grid.innerHTML = cards.map(c => `
    <div class="dash-card">
      <div class="label">${c.label}</div>
      <div class="value">${c.value}</div>
      <div class="sub">${c.sub}</div>
    </div>
  `).join('');
}

// ─── Files ────────────────────────────────────────────────────────────
async function loadFiles() {
  const data = await api('files?path=.');
  const list = document.getElementById('filesList');
  if (data.files) {
    const files = data.files.split('\n').filter(f => f && !f.includes('truncated'));
    list.innerHTML = files.map(f => `<div class="file-item" data-path="${f}">${f}</div>`).join('');
    list.querySelectorAll('.file-item').forEach(item => {
      item.onclick = () => readFile(item.dataset.path, item);
    });
  }
}

async function readFile(path, el) {
  document.querySelectorAll('.file-item').forEach(f => f.classList.remove('active'));
  el.classList.add('active');
  const data = await api('files/read?path=' + encodeURIComponent(path));
  const content = document.getElementById('filesContent');
  if (data.error) {
    content.innerHTML = `<div class="files-placeholder">${data.error}</div>`;
  } else {
    content.innerHTML = `<pre>${data.content.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</pre>`;
  }
}

// ─── Models ───────────────────────────────────────────────────────────
async function loadModels() {
  const data = await api('models');
  const info = document.getElementById('modelsInfo');
  info.innerHTML = `
    <div class="info-row">
      <div class="info-item"><div class="label">Primary</div><div class="value">${data.primary}</div></div>
      <div class="info-item"><div class="label">Last Used</div><div class="value">${data.last_used || '—'}</div></div>
      <div class="info-item"><div class="label">Chain Length</div><div class="value">${data.chain.length}</div></div>
    </div>
  `;
  const list = document.getElementById('modelsList');
  list.innerHTML = data.chain.map((m, i) => `
    <div class="model-card ${i === 0 ? 'primary' : ''}" data-model="${m}">
      <span class="model-name">${m}</span>
      <span class="model-badge">${i === 0 ? 'PRIMARY' : 'FALLBACK ' + i}</span>
    </div>
  `).join('');
  list.querySelectorAll('.model-card').forEach(card => {
    card.onclick = async () => {
      await api('models/set', 'POST', {model: card.dataset.model});
      loadModels();
    };
  });
}

// ─── Tools ────────────────────────────────────────────────────────────
let allTools = [];
async function loadTools() {
  const data = await api('tools');
  allTools = data.tools;
  renderTools(allTools);
}

function renderTools(tools) {
  const grid = document.getElementById('toolsGrid');
  grid.innerHTML = tools.map(t => `
    <div class="tool-card">
      <div class="tool-header">
        <span class="tool-name">${t.name}</span>
        <span class="tool-badge ${t.mutating ? 'mutating' : 'safe'}">${t.mutating ? 'MUTATING' : 'SAFE'}</span>
      </div>
      <div class="tool-desc">${t.description}</div>
    </div>
  `).join('');
}

// ─── Settings ─────────────────────────────────────────────────────────
async function loadSettings() {
  settingsData = await api('settings');
  const tabs = document.getElementById('settingsTabs');
  tabs.innerHTML = settingsSections.map((s, i) =>
    `<button class="settings-tab ${i === 0 ? 'active' : ''}" data-section="${s}">${s.charAt(0).toUpperCase() + s.slice(1)}</button>`
  ).join('');
  tabs.querySelectorAll('.settings-tab').forEach(tab => {
    tab.onclick = () => {
      tabs.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      renderSettingsSection(tab.dataset.section);
    };
  });
  renderSettingsSection(settingsSections[0]);
}

function renderSettingsSection(section) {
  const content = document.getElementById('settingsContent');
  const fields = settingsFields[section] || [];
  const data = settingsData[section] || {};

  content.innerHTML = fields.map(f => {
    const value = data[f.key];
    const path = section + '.' + f.key;
    if (f.type === 'bool') {
      return `
        <div class="setting-row">
          <div><div class="setting-label">${f.label}</div></div>
          <label class="toggle-switch">
            <input type="checkbox" data-path="${path}" ${value ? 'checked' : ''}>
            <span class="toggle-slider"></span>
          </label>
        </div>`;
    }
    if (f.type === 'list') {
      return `
        <div class="setting-row">
          <div><div class="setting-label">${f.label}</div><div class="setting-hint">Comma-separated</div></div>
          <input class="setting-input" type="text" data-path="${path}" data-type="list" value="${Array.isArray(value) ? value.join(', ') : value || ''}">
        </div>`;
    }
    return `
      <div class="setting-row">
        <div><div class="setting-label">${f.label}</div></div>
        <input class="setting-input" type="text" data-path="${path}" value="${value !== null ? value : ''}">
      </div>`;
  }).join('');

  // Wire up changes
  content.querySelectorAll('input[data-path]').forEach(input => {
    const event = input.type === 'checkbox' ? 'change' : 'change';
    input.addEventListener(event, async () => {
      let val = input.type === 'checkbox' ? input.checked : input.value;
      await api('settings', 'POST', {path: input.dataset.path, value: val});
      // Refresh settings data
      settingsData = await api('settings');
    });
  });
}

// ─── Confirm Modal ────────────────────────────────────────────────────
function showConfirmModal(id, description) {
  const modal = document.getElementById('confirmModal');
  document.getElementById('confirmText').textContent = description;
  modal.style.display = 'flex';

  const approve = document.getElementById('confirmApprove');
  const deny = document.getElementById('confirmDeny');

  const cleanup = () => { modal.style.display = 'none'; };
  approve.onclick = () => { sendWS({type:'confirm', id, approved:true}); cleanup(); };
  deny.onclick = () => { sendWS({type:'confirm', id, approved:false}); cleanup(); };
}

// ─── Theme ────────────────────────────────────────────────────────────
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.classList.contains('dark');
  html.classList.toggle('dark');
  html.classList.toggle('light');
}

// ─── Init ─────────────────────────────────────────────────────────────
function init() {
  // Navigation
  document.querySelectorAll('.nav-item').forEach(item => {
    item.onclick = () => switchView(item.dataset.view);
  });

  // Sidebar toggle
  document.getElementById('sidebarToggle').onclick = () => {
    document.getElementById('sidebar').classList.toggle('collapsed');
  };

  // Theme toggle
  document.getElementById('themeToggle').onclick = toggleTheme;

  // Chat
  const input = document.getElementById('chatInput');
  document.getElementById('btnSend').onclick = sendMessage;
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 200) + 'px';
  });

  // Quick prompts
  document.querySelectorAll('.quick-prompt').forEach(btn => {
    btn.onclick = () => { input.value = btn.dataset.prompt; sendMessage(); };
  });

  // Chat actions
  document.getElementById('btnReset').onclick = async () => {
    await api('chat/reset', 'POST');
    document.getElementById('chatMessages').innerHTML = `
      <div class="welcome-msg">
        <h3>Welcome to DevOrbit</h3>
        <p>Ask me to code, search the web, browse, edit files, run commands, and more.</p>
      </div>`;
  };
  document.getElementById('btnReflect').onclick = async () => {
    const data = await api('chat/reflect', 'POST');
    if (data.ok) addMessage('assistant', data.response);
  };
  document.getElementById('btnApprove').onclick = async () => {
    const data = await api('approve/toggle', 'POST');
    document.getElementById('approveLabel').textContent = 'Auto-approve: ' + (data.auto_approve ? 'ON' : 'OFF');
  };

  // Dashboard refresh
  document.getElementById('btnRefreshDash').onclick = loadDashboard;

  // Files refresh
  document.getElementById('btnRefreshFiles').onclick = loadFiles;

  // Tool search
  document.getElementById('toolSearch').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    renderTools(allTools.filter(t => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)));
  });

  // Settings actions
  document.getElementById('btnSettingsShow').onclick = async () => {
    const data = await api('settings');
    addMessage('system', JSON.stringify(data, null, 2));
    switchView('chat');
  };
  document.getElementById('btnSettingsReset').onclick = async () => {
    if (confirm('Reset all settings to defaults?')) {
      await api('settings/reset', 'POST');
      loadSettings();
    }
  };

  // Connect WebSocket
  connectWS();

  // Load initial approve state
  api('status').then(data => {
    document.getElementById('approveLabel').textContent = 'Auto-approve: ' + (data.auto_approve ? 'ON' : 'OFF');
  });
}

document.addEventListener('DOMContentLoaded', init);
})();
