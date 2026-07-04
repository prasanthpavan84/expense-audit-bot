// Tab Navigation
const navItems = document.querySelectorAll('.nav-item');
const tabPanels = document.querySelectorAll('.tab-panel');

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const targetTab = item.getAttribute('data-tab');
        
        // Update nav items
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        // Update panels
        tabPanels.forEach(panel => {
            if (panel.id === `panel-${targetTab}`) {
                panel.classList.add('active');
            } else {
                panel.classList.remove('active');
            }
        });
        
        // Special callback routines on panel activations
        if (targetTab === 'workflow') {
            loadMermaidGraph();
            loadYamlDetails();
        } else if (targetTab === 'agents') {
            loadAgentRegistry();
        } else if (targetTab === 'tools') {
            loadToolRegistry();
        } else if (targetTab === 'health') {
            loadHealthStatus();
        } else if (targetTab === 'developer') {
            loadDeveloperData();
        } else if (targetTab === 'knowledge') {
            loadKnowledgeBase();
        } else if (targetTab === 'replay') {
            loadHistoricalAudits();
        } else if (targetTab === 'evaluation') {
            loadEvaluationReport();
        } else if (targetTab === 'benchmarks') {
            loadBenchmarkHistory();
        }
    });
});

// Theme Toggle logic
const themeSelect = document.getElementById('theme-select');
themeSelect.addEventListener('change', (e) => {
    const selected = e.target.value;
    if (selected === 'system') {
        const darkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', darkScheme ? 'dark' : 'light');
    } else {
        document.documentElement.setAttribute('data-theme', selected);
    }
});

// Notifications
const bellIcon = document.querySelector('.notifications-bell');
const notifDropdown = document.getElementById('notif-dropdown');
const notifList = document.getElementById('notif-list');
const notifCount = document.getElementById('notif-count');
let notifications = [];

bellIcon.addEventListener('click', (e) => {
    e.stopPropagation();
    notifDropdown.classList.toggle('show');
});

document.addEventListener('click', () => {
    notifDropdown.classList.remove('show');
});

function addNotification(title, type = 'info') {
    const timeStr = new Date().toLocaleTimeString();
    notifications.unshift({ title, type, time: timeStr });
    
    // Update count
    notifCount.textContent = notifications.length;
    
    // Update list
    notifList.innerHTML = notifications.map(n => `
        <div class="notif-item">
            <strong>${n.title}</strong>
            <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.2rem;">${n.time}</div>
        </div>
    `).join('');
}

// WebSocket Live updates
let ws = null;
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/console`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log("WebSocket connected to Console Event Hub.");
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleConsoleEvent(data.event, data.payload);
        } catch (err) {
            console.error("Error parsing websocket message:", err);
        }
    };
    
    ws.onclose = () => {
        console.log("WebSocket connection closed. Reconnecting in 5s...");
        setTimeout(connectWebSocket, 5000);
    };
}

const liveTimeline = document.getElementById('live-timeline-log');
const auditProgressBar = document.getElementById('audit-progress-bar');

function handleConsoleEvent(event, payload) {
    console.log(`Console Event [${event}]:`, payload);
    
    const timeStr = new Date().toLocaleTimeString();
    let nodeHtml = '';
    
    if (event === "WorkflowStarted") {
        liveTimeline.innerHTML = '';
        auditProgressBar.style.display = 'block';
        nodeHtml = `
            <div class="timeline-node running">
                <div class="node-time">${timeStr}</div>
                <div class="node-content">
                    <div class="node-title">Workflow '${payload.workflow}' Started</div>
                    <div class="node-meta">Correlation ID: ${payload.correlation_id} | Steps: ${payload.steps.join(' → ')}</div>
                </div>
            </div>
        `;
        addNotification(`Workflow '${payload.workflow}' started`, 'info');
    } 
    else if (event === "AgentStarted") {
        nodeHtml = `
            <div class="timeline-node running">
                <div class="node-time">${timeStr}</div>
                <div class="node-content">
                    <div class="node-title">Agent '${payload.agent}' Active</div>
                    <div class="node-meta">Audit scope loaded. Running reasoning cycles...</div>
                </div>
            </div>
        `;
        // Highlight in Mermaid graph
        highlightMermaidNode(payload.agent, 'running');
    }
    else if (event === "AgentCompleted") {
        nodeHtml = `
            <div class="timeline-node completed">
                <div class="node-time">${timeStr}</div>
                <div class="node-content">
                    <div class="node-title">Agent '${payload.agent}' Completed</div>
                    <div class="node-meta">Latency: ${payload.latency_ms.toFixed(1)} ms | ${payload.explanation}</div>
                </div>
            </div>
        `;
        highlightMermaidNode(payload.agent, 'completed');
    }
    else if (event === "AgentFailed") {
        nodeHtml = `
            <div class="timeline-node failed">
                <div class="node-time">${timeStr}</div>
                <div class="node-content">
                    <div class="node-title">Agent '${payload.agent}' Failed</div>
                    <div class="node-meta">${payload.explanation}</div>
                </div>
            </div>
        `;
        highlightMermaidNode(payload.agent, 'failed');
        addNotification(`Agent '${payload.agent}' failed!`, 'danger');
    }
    else if (event === "WorkflowCompleted") {
        auditProgressBar.style.display = 'none';
        nodeHtml = `
            <div class="timeline-node completed" style="border-left-color: var(--accent-success);">
                <div class="node-time">${timeStr}</div>
                <div class="node-content">
                    <div class="node-title">Workflow Execution Finished</div>
                    <div class="node-meta">Total Duration: ${payload.duration_sec.toFixed(2)} seconds | Status: ${payload.status}</div>
                </div>
            </div>
        `;
        addNotification(`Audit completed successfully`, 'success');
        refreshOverviewStats();
    }
    
    if (nodeHtml) {
        liveTimeline.insertAdjacentHTML('beforeend', nodeHtml);
        liveTimeline.scrollTop = liveTimeline.scrollHeight;
    }
}

// Mermaid graphing
let currentMermaidGraph = '';
async function loadMermaidGraph() {
    try {
        const res = await fetch('/api/v1/workflow/mermaid');
        const data = await res.json();
        currentMermaidGraph = data.mermaid;
        
        const canvas = document.getElementById('mermaid-canvas');
        canvas.removeAttribute('data-processed');
        canvas.innerHTML = currentMermaidGraph;
        
        await mermaid.run({ nodes: [canvas] });
        setupMermaidNodeClicks();
    } catch (err) {
        console.error("Error loading Mermaid graph:", err);
    }
}

function highlightMermaidNode(agentName, status) {
    const nodes = document.querySelectorAll('.mermaid .node');
    nodes.forEach(node => {
        const textNode = node.querySelector('.nodeLabel');
        if (textNode && textNode.textContent.toLowerCase().includes(agentName.replace('_', '').toLowerCase())) {
            node.classList.remove('running-node', 'completed-node', 'failed-node');
            if (status === 'running') node.classList.add('running-node');
            else if (status === 'completed') node.classList.add('completed-node');
            else if (status === 'failed') node.classList.add('failed-node');
        }
    });
}

const agentDrawer = document.getElementById('agent-detail-drawer');
const closeDrawerBtn = document.getElementById('close-drawer-btn');
const agentDrawerContent = document.getElementById('agent-drawer-content');

closeDrawerBtn.addEventListener('click', () => {
    agentDrawer.classList.remove('open');
});

function setupMermaidNodeClicks() {
    const nodes = document.querySelectorAll('.mermaid .node');
    nodes.forEach(node => {
        node.style.cursor = 'pointer';
        node.addEventListener('click', () => {
            const labelText = node.querySelector('.nodeLabel').textContent.trim();
            openAgentDrawer(labelText);
        });
    });
}

async function openAgentDrawer(agentName) {
    agentDrawerContent.innerHTML = '<div class="loading-spinner"></div>';
    agentDrawer.classList.add('open');
    
    // Mappings
    let cleanKey = agentName.toLowerCase().replace(' ', '_');
    if (cleanKey.includes('receipt')) cleanKey = 'receipt_extractor';
    else if (cleanKey.includes('fraud')) cleanKey = 'fraud_agent';
    else if (cleanKey.includes('policy')) cleanKey = 'policy_agent';
    else if (cleanKey.includes('reasoning')) cleanKey = 'reasoning_agent';
    else if (cleanKey.includes('reflection')) cleanKey = 'reflection_agent';
    else if (cleanKey.includes('report')) cleanKey = 'report_agent';
    else if (cleanKey.includes('planner')) cleanKey = 'planner_agent';

    try {
        const res = await fetch('/api/v1/agents/registry');
        const list = await res.json();
        const detail = list.find(a => a.name.toLowerCase().includes(cleanKey.replace('_', '')));
        
        if (detail) {
            agentDrawerContent.innerHTML = `
                <div class="drawer-section">
                    <strong>Agent Name</strong>
                    <div>${detail.name}</div>
                </div>
                <div class="drawer-section">
                    <strong>Status</strong>
                    <span class="badge status-healthy">${detail.health}</span>
                </div>
                <div class="drawer-section">
                    <strong>Runs / Success Rate</strong>
                    <div>${detail.runs} runs (${detail.success_rate})</div>
                </div>
                <div class="drawer-section">
                    <strong>Latency Profile</strong>
                    <div>Average: ${detail.avg_latency_ms} ms | Max: ${detail.max_latency_ms} ms</div>
                </div>
                <div class="drawer-section">
                    <strong>Prompt Version</strong>
                    <div>${detail.prompt_version} (Active)</div>
                </div>
                <div class="drawer-section">
                    <strong>Decision Confidence</strong>
                    <div>${(detail.confidence * 100).toFixed(0)}%</div>
                </div>
                <div class="drawer-section">
                    <strong>Capabilities Supported</strong>
                    <div>OCR parser, transaction validations, pattern mapping.</div>
                </div>
            `;
        } else {
            agentDrawerContent.innerHTML = `<div class="empty-state">No details found for agent '${agentName}'</div>`;
        }
    } catch (err) {
        agentDrawerContent.innerHTML = `<div class="empty-state">Error fetching agent metadata</div>`;
    }
}

// Preloaded scenarios and submissions
const runAuditBtn = document.getElementById('run-audit-btn');
const scenarioSelect = document.getElementById('demo-scenario-select');
const rawInputArea = document.getElementById('raw-input-text');
const userRoleSelect = document.getElementById('user-role-select');
const justificationInput = document.getElementById('justification-text');

async function loadDemoScenarios() {
    try {
        const res = await fetch('/api/v1/demo/scenarios');
        const scenarios = await res.json();
        
        scenarioSelect.innerHTML = '<option value="" disabled selected>-- Select a Preset Capstone Scenario --</option>';
        for (const key in scenarios) {
            const sc = scenarios[key];
            const opt = document.createElement('option');
            opt.value = key;
            opt.textContent = `${sc.name} - ${sc.description}`;
            scenarioSelect.appendChild(opt);
        }
        
        scenarioSelect.addEventListener('change', (e) => {
            const sc = scenarios[e.target.value];
            if (sc) {
                rawInputArea.value = sc.payload.raw_input;
                userRoleSelect.value = sc.payload.user_role;
                justificationInput.value = sc.payload.justification;
            }
        });
    } catch (err) {
        console.error("Error loading presentation scenarios:", err);
    }
}

runAuditBtn.addEventListener('click', async () => {
    const raw_input = rawInputArea.value.trim();
    if (!raw_input) {
        alert("Please enter receipt text or select a demo scenario preset.");
        return;
    }
    
    runAuditBtn.disabled = true;
    runAuditBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Executing...';
    
    try {
        const res = await fetch('/api/v1/audit/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                raw_input,
                user_role: userRoleSelect.value,
                justification: justificationInput.value
            })
        });
        const data = await res.json();
        console.log("Audit complete:", data);
    } catch (err) {
        console.error("Error triggering workflow run:", err);
        addNotification("Audit workflow run failed", "danger");
    } finally {
        runAuditBtn.disabled = false;
        runAuditBtn.innerHTML = '<i class="fa-solid fa-play"></i> Trigger Agentic Audit';
    }
});

// Registries & Health loaders
async function loadAgentRegistry() {
    const tbody = document.getElementById('agents-table-body');
    tbody.innerHTML = '<tr><td colspan="8"><div class="loading-spinner"></div></td></tr>';
    try {
        const res = await fetch('/api/v1/agents/registry');
        const list = await res.json();
        tbody.innerHTML = list.map(a => `
            <tr>
                <td><strong>${a.name}</strong></td>
                <td>${a.prompt_version}</td>
                <td>${a.runs}</td>
                <td>${a.success_rate}</td>
                <td>${a.avg_latency_ms} ms</td>
                <td>${(a.confidence * 100).toFixed(0)}%</td>
                <td><span class="dot healthy" style="display:inline-block; margin-right:5px;"></span> Running</td>
                <td><span class="badge status-healthy">${a.health}</span></td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">Error loading registry</td></tr>';
    }
}

async function loadToolRegistry() {
    const tbody = document.getElementById('tools-table-body');
    tbody.innerHTML = '<tr><td colspan="8"><div class="loading-spinner"></div></td></tr>';
    try {
        const res = await fetch('/api/v1/tools/registry');
        const list = await res.json();
        tbody.innerHTML = list.map(t => `
            <tr>
                <td><strong>${t.capability}</strong></td>
                <td>${t.provider}</td>
                <td><code>${t.mcp_server}</code></td>
                <td>${t.calls}</td>
                <td>${t.success_rate}</td>
                <td>${t.response_time_ms} ms</td>
                <td>${t.availability}</td>
                <td><span class="badge status-healthy">${t.status}</span></td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">Error loading tools</td></tr>';
    }
}

async function loadHealthStatus() {
    const grid = document.getElementById('system-health-grid');
    grid.innerHTML = '<div class="loading-spinner"></div>';
    try {
        const res = await fetch('/api/v1/system/health');
        const health = await res.json();
        grid.innerHTML = Object.entries(health).map(([name, status]) => `
            <div class="health-card">
                <strong>${name}</strong>
                <span class="badge status-${status === 'Healthy' ? 'healthy' : 'offline'}">${status}</span>
            </div>
        `).join('');
    } catch (err) {
        grid.innerHTML = '<div class="empty-state">Error loading system health status</div>';
    }
}

// Developer data
async function loadDeveloperData() {
    const flagsList = document.getElementById('developer-flags-list');
    flagsList.innerHTML = '<div class="loading-spinner"></div>';
    try {
        flagsList.innerHTML = `
            <div class="diag-item ok">
                <span>RAG Service (Knowledge Retrieval)</span>
                <span class="badge status-healthy">ON</span>
            </div>
            <div class="diag-item ok">
                <span>Self-Critique (Reflection)</span>
                <span class="badge status-healthy">ON</span>
            </div>
            <div class="diag-item ok">
                <span>Dynamic Planner</span>
                <span class="badge status-healthy">ON</span>
            </div>
            <div class="diag-item ok">
                <span>Trace Replay Manager</span>
                <span class="badge status-healthy">ON</span>
            </div>
            <div class="diag-item ok">
                <span>Developer Debug console</span>
                <span class="badge status-healthy">ON</span>
            </div>
        `;
    } catch (err) {
        flagsList.innerHTML = '<div class="empty-state">Error loading flags</div>';
    }

    const promptsList = document.getElementById('developer-prompts-list');
    promptsList.innerHTML = '<div class="loading-spinner"></div>';
    try {
        const res = await fetch('/api/v1/prompts/registry');
        const prompts = await res.json();
        promptsList.innerHTML = prompts.map(p => `
            <div class="diag-item ok">
                <div>
                    <strong>${p.prompt}</strong>
                    <div style="font-size:0.75rem; color:var(--text-secondary)">Variables: ${p.variables.join(', ')} | Tokens: ~${p.token_count}</div>
                </div>
                <span class="badge status-healthy">${p.version}</span>
            </div>
        `).join('');
    } catch (err) {
        promptsList.innerHTML = '<div class="empty-state">Error loading prompts</div>';
    }
}

// Replays
async function loadHistoricalAudits() {
    const list = document.getElementById('replay-audits-list');
    list.innerHTML = '<div class="loading-spinner"></div>';
    try {
        const res = await fetch('/api/v1/audit/search');
        const audits = await res.json();
        if (audits.length === 0) {
            list.innerHTML = '<div class="empty-state">No audits recorded yet</div>';
            return;
        }
        list.innerHTML = audits.map(a => `
            <div class="replay-audit-item" onclick="selectAuditForReplay('${a.id}')">
                <div style="display:flex; justify-content:space-between;">
                    <strong>${a.id}</strong>
                    <span class="badge status-${a.status === 'Approved' ? 'healthy' : (a.status === 'Rejected' ? 'offline' : 'warning')}">${a.status}</span>
                </div>
                <div class="replay-audit-meta">${a.merchant} | ${a.currency} ${a.amount}</div>
            </div>
        `).join('');
    } catch (err) {
        list.innerHTML = '<div class="empty-state">Error loading history</div>';
    }
}

async function selectAuditForReplay(auditId) {
    const container = document.getElementById('replay-timeline-container');
    container.innerHTML = '<div class="loading-spinner"></div>';
    
    // Mark item active
    const items = document.querySelectorAll('.replay-audit-item');
    items.forEach(it => {
        if (it.textContent.includes(auditId)) it.classList.add('active');
        else it.classList.remove('active');
    });

    try {
        const res = await fetch(`/api/v1/replay/${auditId}`);
        const data = await res.json();
        
        if (!data || !data.timeline || data.timeline.length === 0) {
            container.innerHTML = '<div class="empty-state">No execution trace data found for this audit</div>';
            return;
        }

        container.innerHTML = `
            <div style="margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color);">
                <h4>Audit ID: ${data.audit_id}</h4>
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem;">
                    Vendor: ${data.expense ? data.expense.merchant : 'N/A'} | Amount: ${data.expense ? data.expense.currency : ''} ${data.expense ? data.expense.amount : ''}
                </div>
            </div>
            <div class="live-timeline">
                ${data.timeline.map(t => {
                    const statusClass = t.event_type.includes('Started') ? 'running' : 'completed';
                    return `
                        <div class="timeline-node ${statusClass}">
                            <div class="node-time">${new Date(t.timestamp * 1000).toLocaleTimeString()}</div>
                            <div class="node-content">
                                <div class="node-title">${t.event_type} (${t.source})</div>
                                <div class="node-meta">${JSON.stringify(t.payload)}</div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (err) {
        container.innerHTML = '<div class="empty-state">Error loading replay timeline</div>';
    }
}

// Evaluation report
async function loadEvaluationReport() {
    const gradeBox = document.getElementById('eval-grade-box');
    const contentBox = document.getElementById('eval-report-content');
    gradeBox.innerHTML = '<div class="loading-spinner"></div>';
    contentBox.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const res = await fetch('/api/v1/evaluation/latest');
        const data = await res.json();
        
        gradeBox.innerHTML = `
            <div class="eval-grade-letter">${data.overall_grade}</div>
            <strong>Strengths</strong>
            <p style="font-size:0.85rem; margin-bottom:1rem;">${data.strengths}</p>
            <strong>Weaknesses</strong>
            <p style="font-size:0.85rem;">${data.weaknesses}</p>
        `;
        
        contentBox.innerHTML = `<pre style="white-space: pre-wrap; font-family: monospace;">${data.report_markdown}</pre>`;
    } catch (err) {
        gradeBox.innerHTML = '<div class="empty-state">N/A</div>';
        contentBox.innerHTML = '<div class="empty-state">Error loading report</div>';
    }
}

// Diagnostics list
async function loadDiagnosticsOverview() {
    const list = document.getElementById('diag-list-overview');
    if (!list) return;
    list.innerHTML = '<div class="loading-spinner"></div>';
    
    const overviewHealth = document.getElementById('health-grid-overview');
    overviewHealth.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const res = await fetch('/api/v1/system/diagnostics');
        const diag = await res.json();
        
        list.innerHTML = Object.entries(diag).map(([name, status]) => `
            <div class="diag-item ${status === 'Healthy' ? 'ok' : 'error'}">
                <span>${name} Service</span>
                <span class="badge status-${status === 'Healthy' ? 'healthy' : 'offline'}">${status}</span>
            </div>
        `).join('');

        overviewHealth.innerHTML = Object.entries(diag).map(([name, status]) => `
            <div class="health-cell">
                <span>${name}</span>
                <span class="dot ${status === 'Healthy' ? 'healthy' : 'offline'}"></span>
            </div>
        `).join('');
    } catch (err) {
        list.innerHTML = '<div class="empty-state">Error loading diagnostics</div>';
    }
}

// Load benchmarks
async function loadBenchmarkHistory() {
    const grid = document.getElementById('benchmark-history-grid');
    grid.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const res = await fetch('/api/v1/evaluation/history');
        const history = await res.json();
        
        grid.innerHTML = `
            <table style="width:100%">
                <thead>
                    <tr>
                        <th>Benchmark Run</th>
                        <th>Accuracy</th>
                        <th>Recall</th>
                        <th>Avg Latency</th>
                        <th>Est Cost</th>
                    </tr>
                </thead>
                <tbody>
                    ${history.map(h => `
                        <tr>
                            <td><strong>${h.benchmark}</strong></td>
                            <td>${h.accuracy.toFixed(1)}%</td>
                            <td>${h.recall.toFixed(1)}%</td>
                            <td>${h.latency_sec.toFixed(3)}s</td>
                            <td>$${h.cost_usd.toFixed(4)} USD</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (err) {
        grid.innerHTML = '<div class="empty-state">Error loading benchmarks history</div>';
    }
}

// Load knowledge chunks
async function loadKnowledgeBase() {
    const list = document.getElementById('knowledge-chunks-list');
    list.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        // Fetch prompts/configs or policy values directly
        const res = await fetch('/api/v1/workflow/definitions');
        const data = await res.json();
        const limits = data.parsed ? (data.parsed.category_limits || {}) : {};
        
        list.innerHTML = `
            <div class="chunk-card">
                <strong>Standard Spending Limit Rules:</strong>
                <p>Meals capped at $50 USD (INR limit: 4,000 INR). Hotel capped at $150 USD (INR limit: 12,000 INR).</p>
            </div>
            <div class="chunk-card">
                <strong>Restricted Vendor Rules:</strong>
                <p>Expenditure at Casinos, Pubs, Bars, and Gambling houses is strictly prohibited.</p>
            </div>
            <div class="chunk-card">
                <strong>Role Multiplier Factors:</strong>
                <p>Associate: 1.0x, Manager: 1.5x, Executive: 3.0x, Intern: 0.5x.</p>
            </div>
        `;
    } catch (err) {
        list.innerHTML = '<div class="empty-state">Error loading policy chunks</div>';
    }
}

// YAML details
async function loadYamlDetails() {
    const pre = document.getElementById('yaml-code-view');
    const meta = document.getElementById('yaml-meta-details');
    
    try {
        const res = await fetch('/api/v1/workflow/definitions');
        const data = await res.json();
        pre.textContent = data.content;
        meta.textContent = `Version: ${data.version} | Hash: ${data.hash} | Loaded: ${data.loaded_time}`;
    } catch (err) {
        pre.textContent = "Error loading workflow YAML configuration details.";
    }
}

// Overview stats
async function refreshOverviewStats() {
    try {
        const res = await fetch('/api/v1/audit/search');
        const audits = await res.json();
        
        const count = audits.length;
        const totalAudited = document.getElementById('stat-total-audited');
        totalAudited.textContent = count;
        
        const rejected = audits.filter(a => a.status === 'Rejected').length;
        const flagged = document.getElementById('stat-flagged-fraud');
        flagged.textContent = rejected;
        
        const successRate = count > 0 ? (((count - rejected) / count) * 100).toFixed(0) + '%' : '100%';
        document.getElementById('stat-compliance-rate').textContent = successRate;
        
        const totalCost = document.getElementById('stat-total-cost');
        totalCost.textContent = `$${(count * 0.00015).toFixed(4)} USD`;
    } catch (err) {
        console.error("Error refreshing stats:", err);
    }
}

// Admin action trigger
async function triggerAdminAction(action) {
    if (action === 'reset_database' && !confirm("Are you sure you want to recreate the database tables? All data will be lost.")) {
        return;
    }
    try {
        const res = await fetch('/api/v1/admin/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        const data = await res.json();
        alert(data.message);
    } catch (err) {
        alert("Error executing admin action");
    }
}

// Initializers
window.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    loadDemoScenarios();
    loadDiagnosticsOverview();
    refreshOverviewStats();
});
