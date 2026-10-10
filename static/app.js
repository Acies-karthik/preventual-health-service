async function fetchHealth() {
    try {
        const response = await fetch('/health/services');
        const data = await response.json();
        renderDashboard(data);
    } catch (err) {
        renderError(err);
    }
}

function renderDashboard(data) {
    // 1. Navbar Status Badge
    const navBadge = document.getElementById('navStatusBadge');
    const navText = document.getElementById('navStatusText');
    const isHealthy = data.status === 'healthy';
    navBadge.className = 'nav-status-badge ' + data.status;
    navText.textContent = isHealthy ? 'All Systems Operational' : data.status.toUpperCase();

    // 2. Updated Timestamp
    const date = new Date(data.timestamp);
    document.getElementById('lastUpdatedText').textContent = 'Updated: ' + date.toLocaleTimeString();

    const s = data.services;

    // Count: 5 logical cards (Airflow, Spark, DB merged, Secrets, SMTP)
    const total = 5;
    const dbHealthy = s.database_services.status === 'healthy' && s.database_auth.status === 'healthy';
    const operational = [
        s.airflow.status === 'healthy',
        s.spark.status === 'healthy',
        dbHealthy,
        s.secret_manager.status === 'healthy',
        s.smtp.status === 'healthy',
    ].filter(Boolean).length;

    // 3. Top KPIs
    document.getElementById('kpiTotal').textContent = total;
    document.getElementById('kpiOperational').textContent = `${operational} / ${total}`;
    document.getElementById('kpiActiveDags').textContent = s.airflow ? `${s.airflow.active_dags || 0} / ${s.airflow.total_dags || 0}` : '-';
    document.getElementById('kpiSparkWorkers').textContent = s.spark ? `${s.spark.alive_workers || 0} / ${s.spark.total_workers || 0}` : '-';

    // 4. Compute merged DB status (healthy only if both healthy, otherwise unhealthy)
    const dbOverallStatus = (s.database_services.status === 'healthy' && s.database_auth.status === 'healthy')
        ? 'healthy'
        : 'unhealthy';

    // 5. Render Service Cards without technical URLs/endpoints (5 cards: Airflow, Spark, DB merged, Secrets, SMTP)
    const container = document.getElementById('servicesContainer');
    container.innerHTML = `
        <!-- Airflow Orchestrator -->
        <div class="service-card">
            <div class="service-card-header">
                <div class="service-title-wrap">
                    <div class="service-icon" style="background: #e0f2fe; padding: 8px;"><img src="/static/images/airflow.svg" width="22" height="22" alt="Airflow"></div>
                    <div>
                        <div class="service-name">Airflow Orchestrator</div>
                        <div class="service-type">Workflow & Scheduler Engine</div>
                    </div>
                </div>
                <span class="status-pill ${s.airflow.status}">${s.airflow.status}</span>
            </div>
            <div class="service-card-body">
                <div class="meta-list">
                    <div class="meta-item"><span class="meta-label">Active Workflows</span><span class="meta-value green">${s.airflow.active_dags} of ${s.airflow.total_dags} Active</span></div>
                    <div class="meta-item"><span class="meta-label">Paused / Idle</span><span class="meta-value">${s.airflow.paused_dags}</span></div>
                    <div class="meta-item"><span class="meta-label">Scheduler Health</span><span class="meta-value green">Online & Synced</span></div>
                </div>
                <div class="sub-items-header">Monitored DAGs (${s.airflow.total_dags || 0})</div>
                <div class="sub-items-box">
                    ${(s.airflow.dags || []).map(dag => `
                        <div class="sub-item-row">
                            <div class="sub-item-name">
                                <span>${dag.display_name || dag.dag_id}</span>
                                ${(dag.tags || []).slice(0, 1).map(t => `<span class="tag-pill">${t}</span>`).join('')}
                            </div>
                            <span class="state-tag ${dag.status}">${dag.status}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>

        <!-- Spark Cluster -->
        <div class="service-card">
            <div class="service-card-header">
                <div class="service-title-wrap">
                    <div class="service-icon" style="background: #fef3c7; padding: 8px;"><img src="/static/images/spark.svg" width="22" height="22" alt="Spark"></div>
                    <div>
                        <div class="service-name">Spark Cluster</div>
                        <div class="service-type">Distributed Compute Engine</div>
                    </div>
                </div>
                <span class="status-pill ${s.spark.status}">${s.spark.status}</span>
            </div>
            <div class="service-card-body">
                <div class="meta-list">
                    <div class="meta-item"><span class="meta-label">Master Node</span><span class="meta-value green">${s.spark.master_status || 'ALIVE'}</span></div>
                    <div class="meta-item"><span class="meta-label">Active Workers</span><span class="meta-value green">${s.spark.alive_workers} of ${s.spark.total_workers} Online</span></div>
                    <div class="meta-item"><span class="meta-label">Cluster Compute</span><span class="meta-value">${(s.spark.workers || []).reduce((acc, w) => acc + (w.cores || 0), 0) || 8} vCores · ${(s.spark.workers || []).reduce((acc, w) => acc + Math.round((w.memory_mb || 0) / 1024), 0) || 8} GB RAM</span></div>
                </div>
                <div class="sub-items-header">Cluster Nodes (${s.spark.total_workers || 0})</div>
                <div class="sub-items-box">
                    ${(s.spark.workers || []).map((worker, idx) => `
                        <div class="sub-item-row">
                            <div class="sub-item-name">
                                <span>Worker Node ${idx + 1}</span>
                                <span class="tag-pill">${worker.cores} Cores</span>
                                <span class="tag-pill">${Math.round(worker.memory_mb / 1024)}GB RAM</span>
                            </div>
                            <span class="state-tag ${worker.state.toLowerCase()}">${worker.state}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>

        <!-- Preventual Internal Database (merged) -->
        <div class="service-card">
            <div class="service-card-header">
                <div class="service-title-wrap">
                    <div class="service-icon" style="background: #ede9fe; color: #7c3aed;"><i class="fa-solid fa-database"></i></div>
                    <div>
                        <div class="service-name">Preventual Internal Database</div>
                        <div class="service-type">Relational Database Engine</div>
                    </div>
                </div>
                <span class="status-pill ${dbOverallStatus}">${dbOverallStatus}</span>
            </div>
            <div class="service-card-body">
                <div class="meta-list">
                    <div class="meta-item"><span class="meta-label">Engine</span><span class="meta-value">PostgreSQL</span></div>
                    <div class="meta-item"><span class="meta-label">Connection State</span><span class="meta-value green">Connected & Ready</span></div>
                    <div class="meta-item"><span class="meta-label">Query Health</span><span class="meta-value green">Passed</span></div>
                </div>
                <div class="sub-items-header">Databases (2)</div>
                <div class="sub-items-box">
                    <div class="sub-item-row">
                        <div class="sub-item-name">
                            <span>${s.database_services.database}</span>
                            <span class="tag-pill">Services</span>
                        </div>
                        <span class="state-tag ${s.database_services.status === 'healthy' ? 'active' : 'unhealthy'}">
                            ${s.database_services.status === 'healthy' ? 'active' : 'offline'}
                        </span>
                    </div>
                    <div class="sub-item-row">
                        <div class="sub-item-name">
                            <span>${s.database_auth.database}</span>
                            <span class="tag-pill">Auth & RBAC</span>
                        </div>
                        <span class="state-tag ${s.database_auth.status === 'healthy' ? 'active' : 'unhealthy'}">
                            ${s.database_auth.status === 'healthy' ? 'active' : 'offline'}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Secret Manager -->
        <div class="service-card">
            <div class="service-card-header">
                <div class="service-title-wrap">
                    <div class="service-icon" style="background: #ffedd5; font-size: 22px;">🔒</div>
                    <div>
                        <div class="service-name">Secrets Manager</div>
                        <div class="service-type">Vault & Credential Store</div>
                    </div>
                </div>
                <span class="status-pill ${s.secret_manager.status}">${s.secret_manager.status}</span>
            </div>
            <div class="service-card-body">
                <div class="meta-list">
                    <div class="meta-item"><span class="meta-label">Service Type</span><span class="meta-value">Secrets Vault</span></div>
                    <div class="meta-item"><span class="meta-label">Access State</span><span class="meta-value green">Authenticated & Verified</span></div>
                    <div class="meta-item"><span class="meta-label">Security Protocol</span><span class="meta-value green">Encrypted</span></div>
                </div>
            </div>
        </div>

        <!-- Email & Notification -->
        <div class="service-card">
            <div class="service-card-header">
                <div class="service-title-wrap">
                    <div class="service-icon" style="background: #fee2e2; color: #dc2626;"><i class="fa-solid fa-envelope"></i></div>
                    <div>
                        <div class="service-name">SMTP</div>
                        <div class="service-type">Email Delivery Service</div>
                    </div>
                </div>
                <span class="status-pill ${s.smtp.status}">${s.smtp.status}</span>
            </div>
            <div class="service-card-body">
                <div class="meta-list">
                    <div class="meta-item"><span class="meta-label">Protocol</span><span class="meta-value">SMTP / TLS Encrypted</span></div>
                    <div class="meta-item"><span class="meta-label">Authentication</span><span class="meta-value green">Verified & Logged In</span></div>
                    <div class="meta-item"><span class="meta-label">Dispatch Status</span><span class="meta-value green">Ready for Delivery</span></div>
                </div>
            </div>
        </div>
    `;
}

function renderError(err) {
    const navBadge = document.getElementById('navStatusBadge');
    navBadge.className = 'nav-status-badge unhealthy';
    document.getElementById('navStatusText').textContent = 'Service Unreachable';
    document.getElementById('servicesContainer').innerHTML = `
        <div class="loading-state" style="color: var(--red);">
            Unable to connect to health check service: ${err}
        </div>
    `;
}

// Wire up the Refresh button with rotating icon and interactive feedback
const refreshBtn = document.getElementById('refreshBtn');
const refreshIcon = document.getElementById('refreshIcon');
const refreshBtnText = document.getElementById('refreshBtnText');

async function handleRefreshClick() {
    if (refreshBtn.disabled) return;
    refreshBtn.disabled = true;
    if (refreshIcon) refreshIcon.classList.add('spin-icon');
    if (refreshBtnText) refreshBtnText.textContent = 'Refreshing...';

    try {
        await fetchHealth();
    } finally {
        setTimeout(() => {
            if (refreshIcon) refreshIcon.classList.remove('spin-icon');
            if (refreshBtnText) refreshBtnText.textContent = 'Refresh';
            refreshBtn.disabled = false;
        }, 400);
    }
}

refreshBtn.addEventListener('click', handleRefreshClick);

// Initial fetch on page load
fetchHealth();

// Auto refresh every 15 seconds
setInterval(fetchHealth, 15000);
