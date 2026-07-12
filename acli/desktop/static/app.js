/* DevOrbit Desktop — Application Logic v2 */
(function() {
'use strict';

// ─── State ────────────────────────────────────────────────────────────
let ws = null;
let currentView = 'chat';
let settingsData = null;
let allTools = [];
let currentFilePath = null;
let originalFileContent = '';
let fileModified = false;
let terminalExpanded = true;

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

// ─── Terminal Output Panel ────────────────────────────────────────────
function termLog(type, message) {
  const body = document.getElementById('terminalBody');
  const time = new Date().toLocaleTimeString();
  const line = document.createElement('div');
  line.className = 'term-line ' + type;
  line.innerHTML = '<span class="timestamp">[' + time + ']</span>' + message.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;
}

function termClear() {
  document.getElementById('terminalBody').innerHTML = '';
}

function termToggle() {
  const panel = document.getElementById('terminalPanel');
  panel.classList.toggle('collapsed');
  const btn = document.getElementById('terminalToggle');
  btn.textContent = panel.classList.contains('collapsed') ? '▸' : '▾';
}

// ─── WebSocket ────────────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(proto + '://' + location.host + '/ws/chat');

  ws.onopen = () => {
    document.querySelector('.status-dot').className = 'status-dot connected';
    document.querySelector('.status-text').textContent = 'Connected';
    termLog('info', 'WebSocket connected');
  };

  ws.onclose = () => {
    document.querySelector('.status-dot').className = 'status-dot error';
    document.querySelector('.status-text').textContent = 'Disconnected';
    termLog('error', 'WebSocket disconnected — reconnecting...');
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
      termLog('success', 'AI response received');
      break;
    case 'system':
      addMessage('system', data.message);
      termLog('info', data.message);
      break;
    case 'status':
      addMessage('status', data.message);
      termLog('info', data.message);
      break;
    case 'error':
      addMessage('error', data.message);
      termLog('error', data.message);
      break;
    case 'tool':
      termLog('tool', data.name + ': ' + (data.description || data.result || ''));
      break;
    case 'confirm':
      showConfirmModal(data.id, data.description);
      termLog('info', 'Confirmation requested: ' + data.description);
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
  const welcome = container.querySelector('.welcome-msg');
  if (welcome) welcome.remove();

  if (role === 'status' || role === 'system') {
    const lastStatus = container.querySelector('.msg.status:last-child');
    if (lastStatus) lastStatus.remove();
  }

  const div = document.createElement('div');
  div.className = 'msg ' + role;

  let formatted = content;
  if (role === 'assistant' || role === 'system') {
    formatted = formatCodeBlocks(content);
  }
  div.innerHTML = formatted;

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function formatCodeBlocks(text) {
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
  termLog('info', 'User: ' + text.substring(0, 100));
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

// ─── Files with Editor ────────────────────────────────────────────────
async function loadFiles() {
  const data = await api('files?path=.');
  const list = document.getElementById('filesList');
  if (data.files) {
    const files = data.files.split('\n').filter(f => f && !f.includes('truncated'));
    list.innerHTML = files.map(f => `<div class="file-item" data-path="${f}">${f}</div>`).join('');
    list.querySelectorAll('.file-item').forEach(item => {
      item.onclick = () => openFile(item.dataset.path, item);
    });
  }
}

async function openFile(path, el) {
  document.querySelectorAll('.file-item').forEach(f => f.classList.remove('active'));
  el.classList.add('active');
  currentFilePath = path;

  const data = await api('files/read?path=' + encodeURIComponent(path));
  const content = document.getElementById('filesContent');

  if (data.error) {
    content.innerHTML = `<div class="files-placeholder">${data.error}</div>`;
    document.getElementById('btnSaveFile').style.display = 'none';
    return;
  }

  originalFileContent = data.content;
  fileModified = false;

  const ext = path.split('.').pop().toLowerCase();
  const langMap = {py:'python', js:'javascript', ts:'typescript', jsx:'javascript', tsx:'typescript',
    html:'html', css:'css', json:'json', md:'markdown', sh:'bash', yml:'yaml', yaml:'yaml',
    go:'go', rs:'rust', java:'java', c:'c', cpp:'cpp', sql:'sql', xml:'xml'};
  const lang = langMap[ext] || 'text';

  content.innerHTML = `
    <div class="editor-toolbar">
      <span class="file-path">${path}</span>
      <span class="file-status" id="fileStatus">${lang}</span>
    </div>
    <div class="editor-container">
      <div class="line-numbers" id="lineNumbers"></div>
      <textarea class="editor-textarea" id="editorTextarea" spellcheck="false">${data.content.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</textarea>
    </div>
  `;

  document.getElementById('btnSaveFile').style.display = '';

  const textarea = document.getElementById('editorTextarea');
  updateLineNumbers(textarea.value);

  textarea.addEventListener('input', () => {
    updateLineNumbers(textarea.value);
    const modified = textarea.value !== originalFileContent;
    if (modified !== fileModified) {
      fileModified = modified;
      const status = document.getElementById('fileStatus');
      status.textContent = modified ? '● Modified' : lang;
      status.className = 'file-status ' + (modified ? 'modified' : '');
    }
  });

  // Tab key support
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      textarea.value = textarea.value.substring(0, start) + '    ' + textarea.value.substring(end);
      textarea.selectionStart = textarea.selectionEnd = start + 4;
      textarea.dispatchEvent(new Event('input'));
    }
  });

  termLog('info', 'Opened file: ' + path);
}

function updateLineNumbers(text) {
  const lines = text.split('\n').length;
  const ln = document.getElementById('lineNumbers');
  if (ln) {
    ln.innerHTML = Array.from({length: lines}, (_, i) => i + 1).join('<br>');
  }
}

async function saveCurrentFile() {
  if (!currentFilePath) return;
  const textarea = document.getElementById('editorTextarea');
  if (!textarea) return;

  const data = await api('files/write', 'POST', {path: currentFilePath, content: textarea.value});
  if (data.ok) {
    originalFileContent = textarea.value;
    fileModified = false;
    const status = document.getElementById('fileStatus');
    status.textContent = '✓ Saved';
    status.className = 'file-status saved';
    setTimeout(() => {
      status.textContent = currentFilePath.split('.').pop();
      status.className = 'file-status';
    }, 2000);
    termLog('success', 'Saved: ' + currentFilePath);
  } else {
    termLog('error', 'Save failed: ' + (data.error || 'unknown'));
  }
}

function showNewFileModal() {
  document.getElementById('newFileModal').style.display = 'flex';
  document.getElementById('newFileName').value = '';
  document.getElementById('newFileName').focus();
}

async function createNewFile() {
  const name = document.getElementById('newFileName').value.trim();
  if (!name) return;

  const data = await api('files/write', 'POST', {path: name, content: ''});
  if (data.ok) {
    document.getElementById('newFileModal').style.display = 'none';
    termLog('success', 'Created: ' + name);
    loadFiles();
    // Auto-open the new file
    setTimeout(() => {
      const item = document.querySelector(`.file-item[data-path="${name}"]`);
      if (item) openFile(name, item);
    }, 200);
  } else {
    termLog('error', 'Create failed: ' + (data.error || 'unknown'));
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
      termLog('info', 'Switched primary model to: ' + card.dataset.model);
      loadModels();
    };
  });
}

// ─── Tools ────────────────────────────────────────────────────────────
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

  content.querySelectorAll('input[data-path]').forEach(input => {
    input.addEventListener('change', async () => {
      let val = input.type === 'checkbox' ? input.checked : input.value;
      await api('settings', 'POST', {path: input.dataset.path, value: val});
      settingsData = await api('settings');
      termLog('info', 'Setting updated: ' + input.dataset.path);
    });
  });
}

// ─── Confirm Modal ────────────────────────────────────────────────────
function showConfirmModal(id, description) {
  const modal = document.getElementById('confirmModal');
  document.getElementById('confirmText').textContent = description;
  modal.style.display = 'flex';

  const cleanup = () => { modal.style.display = 'none'; };
  document.getElementById('confirmApprove').onclick = () => { sendWS({type:'confirm', id, approved:true}); cleanup(); };
  document.getElementById('confirmDeny').onclick = () => { sendWS({type:'confirm', id, approved:false}); cleanup(); };
}

// ─── Theme ────────────────────────────────────────────────────────────
function toggleTheme() {
  const html = document.documentElement;
  html.classList.toggle('dark');
  html.classList.toggle('light');
}

// ─── Init ─────────────────────────────────────────────────────────────
function init() {
  // Navigation
  document.querySelectorAll('.nav-item').forEach(item => {
    item.onclick = () => switchView(item.dataset.view);
  });

  document.getElementById('sidebarToggle').onclick = () => {
    document.getElementById('sidebar').classList.toggle('collapsed');
  };

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
    termLog('info', 'Conversation reset');
  };
  document.getElementById('btnReflect').onclick = async () => {
    termLog('info', 'Reflecting on last answer...');
    const data = await api('chat/reflect', 'POST');
    if (data.ok) addMessage('assistant', data.response);
  };
  document.getElementById('btnApprove').onclick = async () => {
    const data = await api('approve/toggle', 'POST');
    document.getElementById('approveLabel').textContent = 'Auto-approve: ' + (data.auto_approve ? 'ON' : 'OFF');
    termLog('info', 'Auto-approve toggled: ' + (data.auto_approve ? 'ON' : 'OFF'));
  };

  // Terminal panel
  document.getElementById('terminalToggle').onclick = termToggle;
  document.getElementById('terminalClear').onclick = termClear;

  // Dashboard
  document.getElementById('btnRefreshDash').onclick = loadDashboard;

  // Files
  document.getElementById('btnRefreshFiles').onclick = loadFiles;
  document.getElementById('btnSaveFile').onclick = saveCurrentFile;
  document.getElementById('btnNewFile').onclick = showNewFileModal;
  document.getElementById('newFileCancel').onclick = () => { document.getElementById('newFileModal').style.display = 'none'; };
  document.getElementById('newFileCreate').onclick = createNewFile;
  document.getElementById('newFileName').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') createNewFile();
  });

  // Tool search
  document.getElementById('toolSearch').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    renderTools(allTools.filter(t => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)));
  });

  // Settings
  document.getElementById('btnSettingsShow').onclick = async () => {
    const data = await api('settings');
    addMessage('system', JSON.stringify(data, null, 2));
    switchView('chat');
  };
  document.getElementById('btnSettingsReset').onclick = async () => {
    if (confirm('Reset all settings to defaults?')) {
      await api('settings/reset', 'POST');
      loadSettings();
      termLog('info', 'Settings reset to defaults');
    }
  };

  // Connect
  connectWS();
  termLog('info', 'DevOrbit Desktop starting...');

  // Load initial approve state
  api('status').then(data => {
    document.getElementById('approveLabel').textContent = 'Auto-approve: ' + (data.auto_approve ? 'ON' : 'OFF');
  });
}

document.addEventListener('DOMContentLoaded', init);
})();
