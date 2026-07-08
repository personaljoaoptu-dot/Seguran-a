// --- AEGISEYE AI - INTERACTIVE SYSTEM ENGINE ---

document.addEventListener('DOMContentLoaded', () => {
    // --- LOAD USER SESSION & LOGOUT ---
    const userName = sessionStorage.getItem('aegiseye_user_name') || 'Usuário';
    const tenantName = sessionStorage.getItem('aegiseye_tenant_name') || 'Tenant';
    
    const elSidebarUser = document.getElementById('sidebar-user-name');
    const elSidebarTenant = document.getElementById('sidebar-tenant-name');
    const btnLogout = document.getElementById('btn-logout');
    
    if (elSidebarUser) elSidebarUser.innerText = userName;
    if (elSidebarTenant) elSidebarTenant.innerText = tenantName;
    
    if (btnLogout) {
        btnLogout.addEventListener('click', () => {
            sessionStorage.clear();
            window.location.href = 'login.html';
        });
    }

    // --- STATE MANAGEMENT & VARIABLES ---
    let activeTab = 'live';
    let activeCameraId = 0;
    let viewMode = 'single'; // 'single' or 'grid'
    let isEdgeOnline = true; // Heartbeat edge connectivity status
    let liveAnimId = null;
    let liveFrame = 0;
    let soundEnabled = true;
    let activeAlertFilter = 'all';
    
    // Map of camera stream images
    const cameraStreams = {};

    // Sound Toggle
    function toggleSound() {
        soundEnabled = !soundEnabled;
        const btn = document.getElementById('btn-sound-toggle');
        if (btn) {
            btn.innerText = soundEnabled ? '🔊' : '🔇';
            btn.title = soundEnabled ? 'Silenciar Notificações' : 'Ativar Notificações';
        }
        addLog(soundEnabled ? 'Notificações sonoras ativadas.' : 'Notificações sonoras silenciadas.');
    }
    window.toggleSound = toggleSound;

    // Web Audio API synth notification sound
    function playNotificationSound() {
        if (!soundEnabled) return;
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();
            
            // Tone 1: C5 (523.25 Hz)
            const osc1 = ctx.createOscillator();
            const gain1 = ctx.createGain();
            osc1.type = 'sine';
            osc1.frequency.setValueAtTime(523.25, ctx.currentTime);
            gain1.gain.setValueAtTime(0.12, ctx.currentTime);
            gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
            osc1.connect(gain1);
            gain1.connect(ctx.destination);
            
            // Tone 2: G5 (783.99 Hz)
            const osc2 = ctx.createOscillator();
            const gain2 = ctx.createGain();
            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(783.99, ctx.currentTime + 0.08);
            gain2.gain.setValueAtTime(0.0, ctx.currentTime);
            gain2.gain.setValueAtTime(0.12, ctx.currentTime + 0.08);
            gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
            osc2.connect(gain2);
            gain2.connect(ctx.destination);
            
            osc1.start(ctx.currentTime);
            osc1.stop(ctx.currentTime + 0.25);
            osc2.start(ctx.currentTime + 0.08);
            osc2.stop(ctx.currentTime + 0.35);
        } catch (e) {
            console.error("Audio Notification error:", e);
        }
    }

    // Set Alert Filter
    function setAlertFilter(filterValue) {
        activeAlertFilter = filterValue;
        
        // Update button styles
        document.querySelectorAll('.alert-filters .filter-btn').forEach(btn => {
            btn.classList.remove('active');
            btn.style.background = 'var(--slate-950)';
            btn.style.color = 'var(--slate-400)';
            btn.style.border = '1px solid var(--slate-800)';
        });
        
        const activeBtn = document.getElementById(`filter-btn-${filterValue}`);
        if (activeBtn) {
            activeBtn.classList.add('active');
            activeBtn.style.background = 'var(--color-primary)';
            activeBtn.style.color = '#000';
            activeBtn.style.border = 'none';
        }
        
        updateAlertsQueueHTML();
    }
    window.setAlertFilter = setAlertFilter;

    function getStreamHost(camId) {
        const host = window.location.hostname;
        if (host === 'app.aegiseye.com.br' || host === '144.91.121.55') {
            return `cam-${camId}.localhost`;
        }
        if (host === 'localhost' || host === '127.0.0.1') {
            return '127.0.0.1';
        }
        return host;
    }

    function updateActiveStreams() {
        cameraList.forEach(cam => {
            if (!cameraStreams[cam.id]) {
                cameraStreams[cam.id] = new Image();
            }
            const img = cameraStreams[cam.id];
            
            const isCamOnline = (cam.status === 'online' || cam.status === 'warning') && isEdgeOnline;
            
            if (isCamOnline && cam.rtsp) {
                // If in Grid mode, load all streams. If in Single mode, only load activeCameraId.
                const shouldLoad = (viewMode === 'grid') || (viewMode === 'single' && cam.id === activeCameraId);
                
                if (shouldLoad) {
                    const tenantId = sessionStorage.getItem('aegiseye_tenant_id') || 'a7974ee4-329c-4c06-a57a-0377bcae242e';
                    const userId = sessionStorage.getItem('aegiseye_user_id') || '';
                    const streamUrl = `http://${getStreamHost(cam.id)}:8082/stream?rtsp=${encodeURIComponent(cam.rtsp)}&camera_id=${encodeURIComponent(cam.db_id || cam.id)}&camera_name=${encodeURIComponent(cam.name)}&tenant_id=${encodeURIComponent(tenantId)}&user_id=${encodeURIComponent(userId)}`;
                    if (img.src !== streamUrl) {
                        img.src = streamUrl;
                    }
                } else {
                    if (img.src !== '') {
                        img.src = '';
                    }
                }
            } else {
                if (img.src !== '') {
                    img.src = '';
                }
            }
        });
    }
    let isSuspiciousActive = false;
    let suspiciousPhase = 0; // 0: enter, 1: browse, 2: conceal, 3: exit
    let modalAnimId = null;
    let modalFrame = 0;
    let currentModalAlert = null;
    let isHeatmapActive = true;
    window.heatmapValues = {
        bebidas: 15,
        corr1: 10,
        caixas: 6,
        corr2: 3
    };
    let statsAlertsCount = 0;
    let statsSavedValue = 0;
    let nextAlertId = 1;
    
    // Map editor state variables
    let isEditingMap = false;
    let mapElements = [];
    let selectedElementId = null;
    let isDragging = false;
    let isResizing = false;
    let dragOffset = { x: 0, y: 0 };
    const resizeHandleSize = 12;

    let cameraList = [
        { id: 0, name: "Corredor 1 (Mercearia)", status: "online", device: "Intelbras VIP 3230 B", rtsp: "rtsp://192.168.1.100/ch1", profile: "Ocultamento / Suspeita", type: "aisle" },
        { id: 1, name: "Corredor 2 (Biscoitos)", status: "online", device: "Dahua HDW1230S", rtsp: "rtsp://192.168.1.100/ch2", profile: "Ocultamento / Fluxo de Pessoas", type: "aisle" },
        { id: 2, name: "Bebidas Finas", status: "warning", device: "Hikvision DS-2CD2021G1", rtsp: "rtsp://192.168.1.100/ch3", profile: "Permanência Alta / Ocultamento", type: "liquor" },
        { id: 3, name: "Caixa 1", status: "online", device: "Hikvision DS-2CD1023G0", rtsp: "rtsp://192.168.1.100/ch4", profile: "Desistência / Fila Larga", type: "checkout" },
        { id: 4, name: "Caixa 2 (Autoatendimento)", status: "online", device: "Intelbras VIP 1230 D", rtsp: "rtsp://192.168.1.100/ch5", profile: "Checkout Não Escaneado", type: "checkout" }
    ];

    let editingCameraId = null;

    let alertsList = [];

    // --- DOM ELEMENTS ---
    const tabViews = document.querySelectorAll('.tab-view');
    const navButtons = document.querySelectorAll('.nav-item');
    const viewTitle = document.getElementById('view-title');
    const viewSubtitle = document.getElementById('view-subtitle');

    // Stats Headers
    const elStatsAlertsCount = document.getElementById('stats-alerts-count');
    const elStatsSavedValue = document.getElementById('stats-saved-value');

    // Live Feed elements
    const camButtons = document.querySelectorAll('.cam-select-btn');
    const activeCamTitle = document.getElementById('active-cam-title');
    const videoCanvas = document.getElementById('video-canvas');
    const detectionNotice = document.getElementById('detection-notice');
    // Simulation variables removed
    const consoleLogs = document.getElementById('console-logs');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    const alertsQueueContainer = document.getElementById('alerts-queue-container');
    const activeAlertBadge = document.getElementById('active-alert-badge');

    // Camera Config elements
    const cameraGrid = document.getElementById('camera-grid');
    const cameraAddForm = document.getElementById('camera-add-form');
    const cameraTotalCountBadge = document.getElementById('camera-total-count-badge');

    // SaaS Calculator elements
    const saasCamerasSlider = document.getElementById('saas-cameras-slider');
    const saasLossesSlider = document.getElementById('saas-losses-slider');
    const saasRateSlider = document.getElementById('saas-rate-slider');
    const calcValCameras = document.getElementById('calc-val-cameras');
    const calcValLosses = document.getElementById('calc-val-losses');
    const calcValRate = document.getElementById('calc-val-rate');
    const saasSubscriptionPrice = document.getElementById('saas-subscription-price');
    const saasPlanName = document.getElementById('saas-plan-name');
    const saasRecoveredLosses = document.getElementById('saas-recovered-losses');
    const saasNetSavings = document.getElementById('saas-net-savings');
    const saasAnnualSavings = document.getElementById('saas-annual-savings');
    const saasModuleOps = document.getElementById('saas-module-ops');
    const saasInfraCloud = document.getElementById('saas-infra-cloud');
    const saasInfraCost = document.getElementById('saas-infra-cost');
    const saasInfraDesc = document.getElementById('saas-infra-desc');



    // Heatmap Elements
    const heatmapCanvas = document.getElementById('heatmap-canvas');
    const btnToggleHeatmap = document.getElementById('btn-toggle-heatmap');
    const btnResetHeatmap = document.getElementById('btn-reset-heatmap');

    // --- VMS GRID LAYOUT REBUILD ---
    function rebuildVideoDisplayGridHTML() {
        const gridContainer = document.getElementById('video-display-grid');
        if (!gridContainer) return;
        
        gridContainer.innerHTML = '';
        
        const count = cameraList.length;
        gridContainer.className = '';
        if (count <= 1) {
            gridContainer.classList.add('cols-1');
        } else if (count <= 4) {
            gridContainer.classList.add('cols-2');
        } else if (count <= 9) {
            gridContainer.classList.add('cols-3');
        } else {
            gridContainer.classList.add('cols-4');
        }
        
        cameraList.forEach(cam => {
            const item = document.createElement('div');
            item.className = `grid-cam-item ${cam.id === activeCameraId ? 'active' : ''}`;
            item.setAttribute('data-cam-id', cam.id);
            
            item.addEventListener('click', () => {
                activeCameraId = cam.id;
                viewMode = 'single';
                const modeSelector = document.getElementById('view-mode-selector');
                if (modeSelector) modeSelector.value = 'single';
                
                const singleDisp = document.getElementById('video-display-single');
                const gridDisp = document.getElementById('video-display-grid');
                if (singleDisp) singleDisp.style.display = 'block';
                if (gridDisp) gridDisp.style.display = 'none';
                
                activeCamTitle.innerText = cam.name;
                
                loadCameraLayout(cam.id);
                if (typeof stopEditingMode === 'function') {
                    stopEditingMode();
                }
                
                updateActiveStreams();
                rebuildCameraSelectorsHTML();
                
                isSuspiciousActive = false;
                suspiciousPhase = 0;
                detectionNotice.classList.remove('active');
                detectionNotice.innerText = "Nenhuma atividade suspeita no momento";
                addLog(`Visualizando fluxo em tempo real: ${cam.name} (${cam.device}).`);
            });
            
            const isCamOnline = (cam.status === 'online' || cam.status === 'warning') && isEdgeOnline;
            const indicatorClass = cam.status === 'online' ? 'online' : (cam.status === 'warning' ? 'warning' : 'offline');
            
            item.innerHTML = `
                <canvas class="grid-cam-canvas" id="grid-canvas-${cam.id}" width="400" height="225"></canvas>
                
                <!-- Fallback Grid Placeholder -->
                <div class="offline-placeholder" id="grid-offline-${cam.id}" style="display: ${isCamOnline ? 'none' : 'flex'}">
                    <div class="offline-icon-wrapper">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="offline-icon"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    </div>
                    <h4>SINAL PERDIDO</h4>
                    <p>${!isEdgeOnline ? 'Edge Node Desconectado' : 'Fluxo RTSP Indisponível'}</p>
                </div>
                
                <!-- VMS Translucent Overlay -->
                <div class="grid-cam-overlay">
                    <div class="grid-cam-name">
                        <span class="cam-indicator ${indicatorClass}"></span>
                        ${cam.name}
                    </div>
                    <div class="grid-cam-time" id="grid-time-${cam.id}">--:--:--</div>
                </div>
            `;
            
            gridContainer.appendChild(item);
        });
    }

    // View mode selector change event
    const viewModeSelector = document.getElementById('view-mode-selector');
    if (viewModeSelector) {
        viewModeSelector.addEventListener('change', (e) => {
            viewMode = e.target.value;
            const singleDisp = document.getElementById('video-display-single');
            const gridDisp = document.getElementById('video-display-grid');
            
            if (viewMode === 'single') {
                if (singleDisp) singleDisp.style.display = 'block';
                if (gridDisp) gridDisp.style.display = 'none';
                
                const cam = cameraList.find(c => c.id === activeCameraId);
                if (cam) activeCamTitle.innerText = cam.name;
            } else {
                if (singleDisp) singleDisp.style.display = 'none';
                if (gridDisp) gridDisp.style.display = 'grid';
                
                activeCamTitle.innerText = "Modo Multiview (VMS)";
                rebuildVideoDisplayGridHTML();
            }
            updateActiveStreams();
            rebuildCameraSelectorsHTML();
        });
    }

    // --- INITIALIZATION ---
    updateAlertsQueueHTML();
    updateStatsHeader();
    initSaaSCalculator();
    loadCameraLayout(activeCameraId);
    rebuildCameraSelectorsHTML();
    initLiveVideoEngine();
    initHeatmapEngine();

    // Database integrations
    loadCamerasFromDatabase();
    loadAlertsFromDatabase();
    setInterval(loadAlertsFromDatabase, 5000);

    // Edge Status Heartbeat Loop
    async function checkEdgeStatus() {
        const tenantId = sessionStorage.getItem('aegiseye_tenant_id');
        if (!tenantId) return;
        
        let online = false;
        
        // 1. Try to ping local streamer directly (latency check)
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 1500);
            await fetch(`http://localhost:8082/`, { 
                method: 'GET', 
                mode: 'no-cors',
                signal: controller.signal 
            });
            clearTimeout(timeoutId);
            online = true;
        } catch (localErr) {
            // Local streamer not running or unreachable, fallback to server check
            try {
                const res = await fetch(`/api/edge-status?tenant_id=${tenantId}`);
                if (res.ok) {
                    const data = await res.json();
                    online = data.online;
                }
            } catch (serverErr) {
                online = false;
                const cloudDot = document.getElementById('health-cloud-dot');
                const cloudText = document.getElementById('health-cloud-status');
                if (cloudDot && cloudText) {
                    cloudDot.style.backgroundColor = '#ef4444';
                    cloudText.innerText = 'Offline';
                    cloudText.style.color = '#ef4444';
                }
            }
        }
        
        isEdgeOnline = online;
        updateActiveStreams();
        
        // Update System Health status indicators
        const camDot = document.getElementById('health-camera-dot');
        const camText = document.getElementById('health-camera-status');
        const aiDot = document.getElementById('health-ai-dot');
        const aiText = document.getElementById('health-ai-status');
        const cloudDot = document.getElementById('health-cloud-dot');
        const cloudText = document.getElementById('health-cloud-status');

        if (camDot && camText) {
            const cam = cameraList[activeCameraId];
            const camOnline = cam && (cam.status === 'online' || cam.status === 'warning') && isEdgeOnline;
            camDot.style.backgroundColor = camOnline ? '#10b981' : '#ef4444';
            camText.innerText = camOnline ? 'Online' : 'Offline';
            camText.style.color = camOnline ? '#10b981' : '#ef4444';
        }
        if (aiDot && aiText) {
            aiDot.style.backgroundColor = isEdgeOnline ? '#10b981' : '#ef4444';
            aiText.innerText = isEdgeOnline ? 'Ativa' : 'Inativa';
            aiText.style.color = isEdgeOnline ? '#10b981' : '#ef4444';
        }
        if (cloudDot && cloudText && online) {
            cloudDot.style.backgroundColor = '#10b981';
            cloudText.innerText = 'Online';
            cloudText.style.color = '#10b981';
        }

        // Trigger queue view update to handle lost connection screen
        updateAlertsQueueHTML();

        const dot = document.querySelector('.pulse-dot');
        const text = document.querySelector('.status-text');
        if (dot && text) {
            if (online) {
                dot.className = "pulse-dot green";
                text.innerHTML = "Edge Node: <strong>Conectado</strong>";
            } else {
                dot.className = "pulse-dot red";
                text.innerHTML = "Edge Node: <strong>Desconectado</strong>";
            }
        }
        
        // Update single fallback visibility
        const offlinePlaceholder = document.getElementById('offline-placeholder');
        if (offlinePlaceholder) {
            const cam = cameraList.find(c => c.id === activeCameraId);
            const isCamOnline = cam && (cam.status === 'online' || cam.status === 'warning') && isEdgeOnline;
            offlinePlaceholder.style.display = isCamOnline ? 'none' : 'flex';
        }
        
        // Update grid placeholders visibility
        if (viewMode === 'grid') {
            cameraList.forEach(cam => {
                const gridOffline = document.getElementById(`grid-offline-${cam.id}`);
                if (gridOffline) {
                    const isCamOnline = (cam.status === 'online' || cam.status === 'warning') && isEdgeOnline;
                    gridOffline.style.display = isCamOnline ? 'none' : 'flex';
                    const statusText = gridOffline.querySelector('p');
                    if (statusText) {
                        statusText.innerText = !isEdgeOnline ? 'Edge Node Desconectado' : 'Fluxo RTSP Indisponível';
                    }
                }
            });
        }
    }
    checkEdgeStatus();
    setInterval(checkEdgeStatus, 8000);

    // --- ROUTING / TAB TOGGLE ---
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            activeTab = targetTab;
            
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            tabViews.forEach(view => {
                view.classList.remove('active');
                if (view.id === `view-${targetTab}`) {
                    view.classList.add('active');
                }
            });

            // Update Header Title / Subtitle
            if (targetTab === 'live') {
                viewTitle.innerText = "Monitoramento Live";
                viewSubtitle.innerText = "Acompanhamento em tempo real e inteligência local";
            } else if (targetTab === 'analytics') {
                viewTitle.innerText = "Analytics & Heatmaps";
                viewSubtitle.innerText = "Métricas agregadas e análise espacial de perdas";
                if (typeof syncAnalyticsData === 'function') {
                    syncAnalyticsData();
                } else {
                    setTimeout(drawHeatmap, 50);
                }
            } else if (targetTab === 'cameras') {
                viewTitle.innerText = "Gerenciar Câmeras";
                viewSubtitle.innerText = "Configuração de conexões RTSP locais e inteligência por câmera";
            } else if (targetTab === 'saas') {
                viewTitle.innerText = "Simulador SaaS & ROI";
                viewSubtitle.innerText = "Simule e entenda a viabilidade comercial do projeto AegisEye AI";
            } else if (targetTab === 'settings') {
                viewTitle.innerText = "Configurações";
                viewSubtitle.innerText = "Parâmetros operacionais do sistema, webhook e chaves de segurança";
                if (typeof window.loadSettings === 'function') {
                    window.loadSettings();
                }
            }
        });
    });

    setInterval(() => {
        if (activeTab === 'analytics' && typeof syncAnalyticsData === 'function') {
            syncAnalyticsData();
        }
    }, 5000);

    // --- SYSTEM LOGS CONSOLE ---
    function addLog(text, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        line.innerText = `[${timestamp}] ${text}`;
        consoleLogs.appendChild(line);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    btnClearLogs.addEventListener('click', () => {
        consoleLogs.innerHTML = '';
        addLog('Logs limpos pelo operador.');
    });

    // --- ALERTS QUEUE MANAGEMENT ---
    function updateAlertsQueueHTML() {
        alertsQueueContainer.innerHTML = '';
        
        if (!isEdgeOnline) {
            activeAlertBadge.innerText = `0 ativos`;
            alertsQueueContainer.innerHTML = `
                <div class="empty-alerts-notice" style="text-align: center; padding: 40px 20px; color: #ef4444; border: 1px dashed #ef4444; border-radius: var(--radius-md); background: rgba(239, 68, 68, 0.05);">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 32px; height: 32px; margin-bottom: 8px; color: #ef4444;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    <p style="font-weight: bold; font-size: 13px;">Conexão Perdida: Aguardando sinal do Edge</p>
                </div>
            `;
            return;
        }

        // Filter out alerts with invalid confidence score
        const validAlerts = alertsList.filter(alert => 
            alert.confidence && 
            alert.confidence !== 'undefined' && 
            alert.confidence !== undefined
        );

        activeAlertBadge.innerText = `${validAlerts.length} ativos`;
        
        let filteredAlerts = validAlerts;
        if (activeAlertFilter !== 'all') {
            filteredAlerts = validAlerts.filter(a => a.severity === activeAlertFilter);
        }

        if (filteredAlerts.length === 0) {
            alertsQueueContainer.innerHTML = `
                <div class="empty-alerts-notice" style="text-align: center; padding: 40px 20px; color: var(--slate-600); border: 1px dashed var(--slate-800); border-radius: var(--radius-md);">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 32px; height: 32px; margin-bottom: 8px; opacity: 0.5;"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/></svg>
                    <p>Nenhum alerta detectado até o momento</p>
                </div>
            `;
            return;
        }

        filteredAlerts.forEach(alert => {
            const card = document.createElement('div');
            card.className = `alert-card ${alert.severity} ${alert.id === 1 ? 'anim-pulse-card' : ''}`;
            card.setAttribute('data-alert-id', alert.id);

            const labelSeverity = alert.severity === 'critical' ? 'Crítico' : (alert.severity === 'warning' ? 'Atenção' : 'Médio');
            const confClass = alert.severity === 'critical' ? 'text-rose' : (alert.severity === 'warning' ? 'text-amber' : 'text-cyan');

            const videoBtn = alert.video_url ? `
                <button class="btn-view-evidence action-btn" data-alert-id="${alert.id}" title="Ver Vídeo da Evidência" style="padding: 6px 12px; background: var(--indigo-600); font-size: 11px; border-radius: var(--radius-sm); color: #fff; border: none; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 12px; height: 12px;"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    Ver Vídeo
                </button>
            ` : '';

            card.innerHTML = `
                <div class="alert-card-header">
                    <span class="severity-badge ${alert.severity}">${labelSeverity}</span>
                    <span class="alert-time">${alert.time}</span>
                </div>
                <div class="alert-card-body">
                    <h3 class="alert-title">${alert.title}</h3>
                    <p class="alert-details">${alert.details}</p>
                    <div class="alert-meta">
                        <span>Cam: <strong>${alert.camera}</strong></span>
                        <span>Confiança: <strong class="${confClass}">${alert.confidence}%</strong></span>
                    </div>
                </div>
                <div class="alert-card-actions" style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                    <div class="alert-feedback-btns">
                        <button class="btn-feedback correct" title="Confirmar Alerta" data-alert-id="${alert.id}">✓</button>
                        <button class="btn-feedback incorrect" title="Falso Positivo" data-alert-id="${alert.id}">✗</button>
                    </div>
                    ${videoBtn}
                </div>
            `;
            alertsQueueContainer.appendChild(card);
        });

        document.querySelectorAll('.btn-feedback.correct').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.getAttribute('data-alert-id');
                handleAlertFeedback(id, true);
            });
        });

        document.querySelectorAll('.btn-feedback.incorrect').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.getAttribute('data-alert-id');
                handleAlertFeedback(id, false);
            });
        });

        document.querySelectorAll('.btn-view-evidence').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const button = e.currentTarget;
                const id = button.getAttribute('data-alert-id');
                openEvidenceModal(id);
            });
        });
    }

    // --- VIDEO EVIDENCE MODAL ENGINE ---
    const modalEvidence = document.getElementById('modal-alert-evidence');
    const modalVideo = document.getElementById('modal-evidence-video');
    const modalTitle = document.getElementById('modal-alert-title');
    const modalCamera = document.getElementById('modal-alert-camera');
    const modalDetails = document.getElementById('modal-alert-details');
    const modalConfidence = document.getElementById('modal-alert-confidence');
    const modalBtnConfirm = document.getElementById('modal-btn-confirm');
    const modalBtnDiscard = document.getElementById('modal-btn-discard');
    const btnCloseModal = document.getElementById('btn-close-modal');

    function openEvidenceModal(id) {
        const alert = alertsList.find(a => a.id === id);
        if (!alert || !alert.video_url) return;

        currentModalAlert = alert;
        if (modalTitle) modalTitle.innerText = `Evidência: ${alert.title}`;
        if (modalCamera) modalCamera.innerText = alert.camera;
        if (modalDetails) modalDetails.innerText = alert.details;
        if (modalConfidence) modalConfidence.innerText = `${alert.confidence}%`;
        
        if (modalVideo) {
            modalVideo.src = alert.video_url;
            modalVideo.load();
            modalVideo.play().catch(err => console.log("Video auto-play failed: ", err));
        }

        if (modalEvidence) modalEvidence.classList.add('active');
    }

    function closeEvidenceModal() {
        if (modalVideo) {
            modalVideo.pause();
            modalVideo.src = '';
        }
        if (modalEvidence) modalEvidence.classList.remove('active');
        currentModalAlert = null;
    }

    if (btnCloseModal) {
        btnCloseModal.addEventListener('click', closeEvidenceModal);
    }
    
    if (modalEvidence) {
        modalEvidence.addEventListener('click', (e) => {
            if (e.target === modalEvidence) {
                closeEvidenceModal();
            }
        });
    }

    if (modalBtnConfirm) {
        modalBtnConfirm.addEventListener('click', () => {
            if (currentModalAlert) {
                handleAlertFeedback(currentModalAlert.id, true);
                closeEvidenceModal();
            }
        });
    }

    if (modalBtnDiscard) {
        modalBtnDiscard.addEventListener('click', () => {
            if (currentModalAlert) {
                handleAlertFeedback(currentModalAlert.id, false);
                closeEvidenceModal();
            }
        });
    }

    function handleAlertFeedback(id, isTruePositive) {
        const idx = alertsList.findIndex(a => a.id === id);
        if (idx === -1) return;
        const alert = alertsList[idx];
        
        if (isTruePositive) {
            addLog(`Alerta #${id} confirmado como VERDADEIRO POSITIVO. Enviado para métricas de perda.`, 'success');
            statsSavedValue += Math.round(150 + Math.random() * 250);
            statsAlertsCount += 1;
        } else {
            addLog(`Alerta #${id} marcado como FALSO ALARME. Atualizando parâmetros da IA de comportamento.`, 'error');
        }

        // Persist resolved status in database
        if (alert.db_id) {
            fetch('/api/resolve-alert', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ alert_id: alert.db_id })
            }).then(res => res.json())
              .then(res => {
                  if (!res.success) {
                      console.error("Erro ao salvar feedback do alerta no servidor:", res.message);
                  }
              }).catch(err => {
                  console.error("Erro de conexão ao salvar feedback do alerta:", err);
              });
        }

        // Add visual fadeout effect to card
        const card = document.querySelector(`.alert-card[data-alert-id="${id}"]`);
        if (card) {
            card.style.opacity = '0';
            card.style.transform = 'scale(0.9)';
            setTimeout(() => {
                alertsList.splice(idx, 1);
                updateAlertsQueueHTML();
                updateStatsHeader();
            }, 300);
        } else {
            alertsList.splice(idx, 1);
            updateAlertsQueueHTML();
            updateStatsHeader();
        }
    }

    function updateStatsHeader() {
        elStatsAlertsCount.innerText = statsAlertsCount;
        elStatsSavedValue.innerText = `R$ ${statsSavedValue.toLocaleString('pt-BR')}`;
    }




    // --- TAB 1: LIVE CANVAS VIDEO ENGINE ---

    const cameraSelectDropdown = document.getElementById('camera-select-dropdown');
    if (cameraSelectDropdown) {
        cameraSelectDropdown.addEventListener('change', (e) => {
            const camId = parseInt(e.target.value);
            activeCameraId = camId;
            
            // Revert to single view when camera is selected directly
            viewMode = 'single';
            const modeSelector = document.getElementById('view-mode-selector');
            if (modeSelector) modeSelector.value = 'single';
            
            const singleDisp = document.getElementById('video-display-single');
            const gridDisp = document.getElementById('video-display-grid');
            if (singleDisp) singleDisp.style.display = 'block';
            if (gridDisp) gridDisp.style.display = 'none';
            
            // Load custom store layout for this camera and turn off edit mode
            loadCameraLayout(camId);
            if (typeof stopEditingMode === 'function') {
                stopEditingMode();
            }
            
            const camData = cameraList.find(c => c.id === camId) || cameraList[0];
            activeCamTitle.innerText = camData.name;
            updateCameraStatusBadge(camId);
            updateActiveStreams();
            rebuildCameraSelectorsHTML();
            
            isSuspiciousActive = false;
            suspiciousPhase = 0;
            detectionNotice.classList.remove('active');
            detectionNotice.innerText = "Nenhuma atividade suspeita no momento";
            
            addLog(`Visualizando fluxo em tempo real: ${camData.name} (${camData.device}).`);
        });
    }

    // Botoes de simulacao removidos

    function loadCameraLayout(id) {
        const key = `aegiseye_map_layout_cam_${id}`;
        const stored = localStorage.getItem(key);
        if (stored) {
            try {
                mapElements = JSON.parse(stored);
                return;
            } catch(e) {
                console.error("Error parsing stored layout:", e);
            }
        }
        
        // Presets per camera
        const cam = cameraList[id];
        if (cam.type === 'checkout') {
            mapElements = [
                { id: 'item_1', type: 'checkout_counter', name: 'Balcão Caixa', x: 200, y: 200, w: 400, h: 120 }
            ];
        } else {
            mapElements = [
                { id: 'item_1', type: 'shelf', name: 'Gôndola Esquerda', x: 100, y: 80, w: 160, h: 280 },
                { id: 'item_2', type: 'shelf', name: 'Gôndola Direita', x: 540, y: 80, w: 160, h: 280 }
            ];
        }
    }

    // --- MAP EDITOR TOOLBAR CONTROLS & EVENT BINDINGS ---
    const btnEditMap = document.getElementById('btn-edit-map');
    const editorActions = document.getElementById('editor-actions');
    const btnSaveMap = document.getElementById('btn-save-map');
    const btnAddShelf = document.getElementById('btn-add-shelf');
    const btnAddCheckout = document.getElementById('btn-add-checkout');
    const btnRemoveElement = document.getElementById('btn-remove-element');
    const btnRestoreDefault = document.getElementById('btn-restore-default');
    const canvasWrapper = document.querySelector('.canvas-wrapper');

    if (btnEditMap) {
        btnEditMap.addEventListener('click', () => {
            isEditingMap = !isEditingMap;
            if (isEditingMap) {
                btnEditMap.innerText = "Parar Edição";
                btnEditMap.classList.add('active');
                if (editorActions) editorActions.style.display = 'flex';
                if (canvasWrapper) canvasWrapper.classList.add('editing');
                addLog("Modo de edição do mapa ativado. Clique e arraste para posicionar, use a âncora inferior direita para redimensionar.");
            } else {
                stopEditingMode();
            }
        });
    }

    function stopEditingMode() {
        isEditingMap = false;
        if (btnEditMap) {
            btnEditMap.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar Layout`;
            btnEditMap.classList.remove('active');
        }
        if (editorActions) editorActions.style.display = 'none';
        if (canvasWrapper) canvasWrapper.classList.remove('editing');
        videoCanvas.style.cursor = 'default';
        selectedElementId = null;
    }

    if (btnSaveMap) {
        btnSaveMap.addEventListener('click', () => {
            const key = `aegiseye_map_layout_cam_${activeCameraId}`;
            localStorage.setItem(key, JSON.stringify(mapElements));
            addLog("Layout do mapa de gôndolas/caixas salvo com sucesso!", "success");
            stopEditingMode();
        });
    }

    if (btnAddShelf) {
        btnAddShelf.addEventListener('click', () => {
            const id = `item_${Date.now()}`;
            mapElements.push({
                id: id,
                type: 'shelf',
                name: `Gôndola #${mapElements.length + 1}`,
                x: 340,
                y: 125,
                w: 120,
                h: 200
            });
            selectedElementId = id;
            addLog("Nova gôndola adicionada ao mapa.");
        });
    }

    if (btnAddCheckout) {
        btnAddCheckout.addEventListener('click', () => {
            const id = `item_${Date.now()}`;
            mapElements.push({
                id: id,
                type: 'checkout_counter',
                name: `Caixa #${mapElements.length + 1}`,
                x: 300,
                y: 175,
                w: 200,
                h: 100
            });
            selectedElementId = id;
            addLog("Nova caixa registradora adicionada ao mapa.");
        });
    }

    if (btnRemoveElement) {
        btnRemoveElement.addEventListener('click', () => {
            if (selectedElementId === null) {
                addLog("Nenhum elemento selecionado para excluir.", "warning");
                return;
            }
            mapElements = mapElements.filter(item => item.id !== selectedElementId);
            selectedElementId = null;
            addLog("Elemento selecionado removido do mapa.");
        });
    }

    if (btnRestoreDefault) {
        btnRestoreDefault.addEventListener('click', () => {
            const key = `aegiseye_map_layout_cam_${activeCameraId}`;
            localStorage.removeItem(key);
            loadCameraLayout(activeCameraId);
            selectedElementId = null;
            addLog("Layout padrão da câmera restaurado.");
        });
    }

    // Mouse Interaction Handlers
    videoCanvas.addEventListener('mousedown', (e) => {
        if (!isEditingMap) return;
        const rect = videoCanvas.getBoundingClientRect();
        const mx = ((e.clientX - rect.left) / rect.width) * videoCanvas.width;
        const my = ((e.clientY - rect.top) / rect.height) * videoCanvas.height;

        // 1. Check resize handle click
        if (selectedElementId !== null) {
            const el = mapElements.find(item => item.id === selectedElementId);
            if (el) {
                const rx = el.x + el.w;
                const ry = el.y + el.h;
                if (mx >= rx - resizeHandleSize && mx <= rx + resizeHandleSize &&
                    my >= ry - resizeHandleSize && my <= ry + resizeHandleSize) {
                    isResizing = true;
                    return;
                }
            }
        }

        // 2. Check element click
        for (let i = mapElements.length - 1; i >= 0; i--) {
            const el = mapElements[i];
            if (mx >= el.x && mx <= el.x + el.w &&
                my >= el.y && my <= el.y + el.h) {
                selectedElementId = el.id;
                isDragging = true;
                dragOffset.x = mx - el.x;
                dragOffset.y = my - el.y;
                return;
            }
        }

        selectedElementId = null;
    });

    videoCanvas.addEventListener('mousemove', (e) => {
        if (!isEditingMap) return;
        const rect = videoCanvas.getBoundingClientRect();
        const mx = ((e.clientX - rect.left) / rect.width) * videoCanvas.width;
        const my = ((e.clientY - rect.top) / rect.height) * videoCanvas.height;

        if (selectedElementId !== null) {
            const el = mapElements.find(item => item.id === selectedElementId);
            if (el) {
                const rx = el.x + el.w;
                const ry = el.y + el.h;
                if (mx >= rx - resizeHandleSize && mx <= rx + resizeHandleSize &&
                    my >= ry - resizeHandleSize && my <= ry + resizeHandleSize) {
                    videoCanvas.style.cursor = 'nwse-resize';
                } else if (mx >= el.x && mx <= el.x + el.w &&
                           my >= el.y && my <= el.y + el.h) {
                    videoCanvas.style.cursor = 'move';
                } else {
                    videoCanvas.style.cursor = 'default';
                }
            }
        } else {
            videoCanvas.style.cursor = 'default';
        }

        if (isDragging && selectedElementId !== null) {
            const el = mapElements.find(item => item.id === selectedElementId);
            if (el) {
                el.x = Math.max(0, Math.min(videoCanvas.width - el.w, mx - dragOffset.x));
                el.y = Math.max(0, Math.min(videoCanvas.height - el.h, my - dragOffset.y));
            }
        } else if (isResizing && selectedElementId !== null) {
            const el = mapElements.find(item => item.id === selectedElementId);
            if (el) {
                el.w = Math.max(40, Math.min(videoCanvas.width - el.x, mx - el.x));
                el.h = Math.max(40, Math.min(videoCanvas.height - el.y, my - el.y));
            }
        }
    });

    videoCanvas.addEventListener('mouseup', () => {
        isDragging = false;
        isResizing = false;
    });

    function initLiveVideoEngine() {
        const ctx = videoCanvas.getContext('2d');
        const W = videoCanvas.width;
        const H = videoCanvas.height;

        // Initialize streams immediately
        updateActiveStreams();

        function renderLive() {
            liveFrame++;
            
            // Check viewMode
            if (viewMode === 'single') {
                const camData = cameraList.find(c => c.id === activeCameraId);
                const offlinePlaceholder = document.getElementById('offline-placeholder');
                
                if (!camData) {
                    ctx.fillStyle = '#060a12';
                    ctx.fillRect(0, 0, W, H);
                    ctx.fillStyle = '#475569';
                    ctx.font = '14px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.fillText("Nenhuma câmera cadastrada neste perfil.", W / 2, H / 2 - 10);
                    ctx.fillText("Vá em 'Conectar Câmera' para iniciar o monitoramento.", W / 2, H / 2 + 15);
                    liveAnimId = requestAnimationFrame(renderLive);
                    return;
                }
                
                const isCamOnline = (camData.status === 'online' || camData.status === 'warning') && isEdgeOnline;
                if (offlinePlaceholder) {
                    offlinePlaceholder.style.display = isCamOnline ? 'none' : 'flex';
                }
                
                if (isCamOnline) {
                    ctx.textAlign = 'left';
                    const img = cameraStreams[camData.id];
                    const isStreaming = img && img.complete && img.naturalWidth !== 0;
                    
                    if (isStreaming) {
                        ctx.drawImage(img, 0, 0, W, H);
                    } else {
                        ctx.fillStyle = '#060a12';
                        ctx.fillRect(0, 0, W, H);
                        
                        // Draw grid guidelines representing store structure
                        ctx.strokeStyle = '#111a2e';
                        ctx.lineWidth = 1;
                        for(let i = 0; i < W; i += 50) {
                            ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, H); ctx.stroke();
                        }
                    }
                    
                    if (!isStreaming) {
                        // Draw map elements dynamically
                        mapElements.forEach(el => {
                            if (el.type === 'shelf') {
                                // Draw outer shelf container
                                ctx.fillStyle = '#0f172a';
                                ctx.fillRect(el.x, el.y, el.w, el.h);
                                
                                // Draw horizontal shelving layers
                                ctx.fillStyle = '#1e293b';
                                const shelfCount = 3;
                                const spacing = el.h / (shelfCount + 1);
                                for (let s = 1; s <= shelfCount; s++) {
                                    ctx.fillRect(el.x, el.y + (s * spacing), el.w, 10);
                                }
                                
                                // Draw colorful products on shelves
                                ctx.fillStyle = '#3b82f6'; ctx.fillRect(el.x + el.w*0.15, el.y + spacing*0.4, Math.max(10, el.w*0.1), spacing*0.5);
                                ctx.fillStyle = '#10b981'; ctx.fillRect(el.x + el.w*0.4, el.y + spacing*0.4, Math.max(8, el.w*0.08), spacing*0.5);
                                ctx.fillStyle = '#eab308'; ctx.fillRect(el.x + el.w*0.7, el.y + spacing*0.4, Math.max(12, el.w*0.11), spacing*0.5);
                            } else if (el.type === 'checkout_counter') {
                                // Draw cash register counters
                                ctx.fillStyle = '#0f172a';
                                ctx.fillRect(el.x, el.y, el.w, el.h);
                                
                                // Draw conveyor belt
                                ctx.fillStyle = '#020617';
                                ctx.fillRect(el.x + el.w*0.05, el.y + el.h*0.15, el.w*0.7, el.h*0.4);
                                
                                // Draw scanner plate
                                ctx.fillStyle = '#22d3ee';
                                ctx.fillRect(el.x + el.w*0.5, el.y + el.h*0.35, el.w*0.1, el.h*0.15);
                            }
                            
                            // Highlight active editing selections
                            if (isEditingMap) {
                                ctx.strokeStyle = el.id === selectedElementId ? '#ff0055' : '#00f0ff';
                                ctx.lineWidth = el.id === selectedElementId ? 2 : 1;
                                ctx.setLineDash([5, 5]);
                                ctx.strokeRect(el.x, el.y, el.w, el.h);
                                ctx.setLineDash([]);
                                
                                ctx.fillStyle = el.id === selectedElementId ? '#ff0055' : '#00f0ff';
                                ctx.font = '10px sans-serif';
                                ctx.fillText(el.name || (el.type === 'shelf' ? 'Gôndola' : 'Caixa'), el.x, el.y - 6);
                                
                                if (el.id === selectedElementId) {
                                    ctx.fillStyle = '#ff0055';
                                    ctx.beginPath();
                                    ctx.arc(el.x + el.w, el.y + el.h, 6, 0, Math.PI * 2);
                                    ctx.fill();
                                }
                            }
                        });

                        // Map editor top notification overlay
                        if (isEditingMap) {
                            ctx.fillStyle = 'rgba(111, 67, 255, 0.9)';
                            ctx.fillRect(0, 0, W, 30);
                            ctx.fillStyle = '#fff';
                            ctx.font = 'bold 11px sans-serif';
                            ctx.textAlign = 'center';
                            ctx.fillText("MODO DE EDIÇÃO DO MAPA DA LOJA - ARRASTE E REDIMENSIONA AS GÔNDOLAS E CAIXAS", W/2, 19);
                            ctx.textAlign = 'start';
                        }
                    }

                    // Bounding boxes simulation removed for SaaS premium audit
                    if (!isStreaming) {
                        ctx.fillStyle = '#0f172a';
                        ctx.fillRect(0, 0, W, H);
                        ctx.fillStyle = '#64748b';
                        ctx.font = 'italic 12px sans-serif';
                        ctx.textAlign = 'center';
                        ctx.fillText(isEdgeOnline ? "Aguardando sinal de vídeo da câmera..." : "Edge Node Offline. Conexão Perdida.", W/2, H/2);
                        detectionNotice.classList.remove('active');
                        detectionNotice.innerText = isEdgeOnline ? "Monitorando: Nenhum alerta de risco detectado" : "Conexão Perdida: Aguardando sinal do Edge";
                    } else {
                        // Real stream is active
                        detectionNotice.classList.remove('active');
                        detectionNotice.innerText = "Monitoramento ao vivo ativo";
                    }

                    // Draw timestamp overlay
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
                    ctx.font = '12px var(--font-body)';
                    ctx.fillText(camData.name.toUpperCase(), 20, 35);
                    ctx.font = '10px monospace';
                    ctx.fillText(new Date().toLocaleString('pt-BR'), 20, 52);
                }
            } else {
                // GRID VIEW RENDER LOOP
                cameraList.forEach(cam => {
                    const gridCanvas = document.getElementById(`grid-canvas-${cam.id}`);
                    if (!gridCanvas) return;
                    
                    const gCtx = gridCanvas.getContext('2d');
                    const gW = gridCanvas.width;
                    const gH = gridCanvas.height;
                    
                    const isCamOnline = (cam.status === 'online' || cam.status === 'warning') && isEdgeOnline;
                    
                    if (isCamOnline) {
                        const img = cameraStreams[cam.id];
                        const isStreaming = img && img.complete && img.naturalWidth !== 0;
                        
                        if (isStreaming) {
                            gCtx.drawImage(img, 0, 0, gW, gH);
                        } else {
                            gCtx.fillStyle = '#060a12';
                            gCtx.fillRect(0, 0, gW, gH);
                            
                            // Draw grid guidelines representing store structure
                            gCtx.strokeStyle = '#111a2e';
                            gCtx.lineWidth = 1;
                            for(let i = 0; i < gW; i += 30) {
                                gCtx.beginPath(); gCtx.moveTo(i, 0); gCtx.lineTo(i, gH); gCtx.stroke();
                            }
                        }
                        
                        // Bounding box simulation removed
                    }
                    
                    // Update overlaid timestamp
                    const timeEl = document.getElementById(`grid-time-${cam.id}`);
                    if (timeEl) {
                        timeEl.innerText = new Date().toLocaleTimeString('pt-BR');
                    }
                });
            }
            
            liveAnimId = requestAnimationFrame(renderLive);
        }
        renderLive();
    }

    // drawTrackObject and triggerNewAlert removed


    // --- TAB 2: STORE HEATMAP ENGINE ---
    async function syncAnalyticsData() {
        const tenantId = sessionStorage.getItem('aegiseye_tenant_id') || 'a7974ee4-329c-4c06-a57a-0377bcae242e';
        const camSelect = document.getElementById('analytics-camera-select');
        const selectedCam = camSelect ? camSelect.value : 'all';
        
        try {
            const res = await fetch(`/api/get-analytics?tenant_id=${encodeURIComponent(tenantId)}&camera_name=${encodeURIComponent(selectedCam)}`);
            const data = await res.json();
            if (data.success) {
                const stats = data.camera_stats || {};
                const hourly = data.hourly_buckets || {};
                
                // Group database values
                const countBebidas = (stats["Bebidas Finas"] || 0) + (stats["Bebidas"] || 0) + (stats["Bebidas Finas (Adega)"] || 0);
                const countCorr1 = (stats["Corredor 1 (Mercearia)"] || 0) + (stats["Corredor 1"] || 0) + (stats["Corr. 1"] || 0);
                const countCorr2 = (stats["Corredor 2 (Biscoitos)"] || 0) + (stats["Corredor 2"] || 0) + (stats["Corr. 2"] || 0);
                const countCaixas = (stats["Caixa 1"] || 0) + (stats["Caixa 2 (Autoatendimento)"] || 0) + (stats["Caixa 2"] || 0) + (stats["Autoatendimento"] || 0) + (stats["Caixas"] || 0);

                // Determine baseline values based on active camera selection
                let baseBebidas = 15;
                let baseCorr1 = 10;
                let baseCaixas = 6;
                let baseCorr2 = 3;
                
                if (selectedCam !== 'all') {
                    baseBebidas = (selectedCam === 'Bebidas Finas' || selectedCam === 'Bebidas Finas (Adega)' || selectedCam === 'Bebidas') ? 15 : 0;
                    baseCorr1 = (selectedCam === 'Corredor 1 (Mercearia)' || selectedCam === 'Corredor 1' || selectedCam === 'Corr. 1') ? 10 : 0;
                    baseCorr2 = (selectedCam === 'Corredor 2 (Biscoitos)' || selectedCam === 'Corredor 2' || selectedCam === 'Corr. 2') ? 3 : 0;
                    baseCaixas = (selectedCam === 'Caixa 1' || selectedCam === 'Caixa 2 (Autoatendimento)' || selectedCam === 'Caixa 2' || selectedCam === 'Autoatendimento' || selectedCam === 'Caixas') ? 6 : 0;
                }

                // Update baseline values with live alerts
                window.heatmapValues = {
                    bebidas: baseBebidas + countBebidas,
                    corr1: baseCorr1 + countCorr1,
                    caixas: baseCaixas + countCaixas,
                    corr2: baseCorr2 + countCorr2
                };
                
                updateCorridorBarChartHTML(window.heatmapValues);
                updateHourlyLineChartHTML(hourly);
                drawHeatmap();
            }
        } catch (err) {
            console.error("Erro ao sincronizar dados de analytics:", err);
        }
    }
    window.syncAnalyticsData = syncAnalyticsData;

    function updateCorridorBarChartHTML(values) {
        const barBebidas = document.getElementById('bar-bebidas');
        const valBebidas = document.getElementById('val-bebidas');
        const barCorr1 = document.getElementById('bar-corr1');
        const valCorr1 = document.getElementById('val-corr1');
        const barCaixas = document.getElementById('bar-caixas');
        const valCaixas = document.getElementById('val-caixas');
        const barCorr2 = document.getElementById('bar-corr2');
        const valCorr2 = document.getElementById('val-corr2');
        
        if (!barBebidas) return;
        
        const maxVal = Math.max(1, values.bebidas, values.corr1, values.caixas, values.corr2);
        const scale = 75 / maxVal;
        
        barBebidas.setAttribute('width', values.bebidas * scale);
        barCorr1.setAttribute('width', values.corr1 * scale);
        barCaixas.setAttribute('width', values.caixas * scale);
        barCorr2.setAttribute('width', values.corr2 * scale);
        
        valBebidas.setAttribute('x', 15 + (values.bebidas * scale) + 3);
        valCorr1.setAttribute('x', 15 + (values.corr1 * scale) + 3);
        valCaixas.setAttribute('x', 15 + (values.caixas * scale) + 3);
        valCorr2.setAttribute('x', 15 + (values.corr2 * scale) + 3);
        
        valBebidas.textContent = values.bebidas;
        valCorr1.textContent = values.corr1;
        valCaixas.textContent = values.caixas;
        valCorr2.textContent = values.corr2;
    }

    function updateHourlyLineChartHTML(hourly) {
        const pathEl = document.getElementById('line-chart-path');
        const c1 = document.getElementById('circle-08h');
        const c2 = document.getElementById('circle-12h');
        const c3 = document.getElementById('circle-16h');
        const c4 = document.getElementById('circle-20h');
        const c5 = document.getElementById('circle-22h');
        
        if (!pathEl) return;
        
        const v1 = 2 + (hourly["08h"] || 0);
        const v2 = 8 + (hourly["12h"] || 0);
        const v3 = 15 + (hourly["16h"] || 0);
        const v4 = 12 + (hourly["20h"] || 0);
        const v5 = 4 + (hourly["22h"] || 0);
        
        const maxVal = Math.max(1, v1, v2, v3, v4, v5);
        const mapY = (val) => 40 - (val / maxVal) * 30;
        
        const y1 = mapY(v1);
        const y2 = mapY(v2);
        const y3 = mapY(v3);
        const y4 = mapY(v4);
        const y5 = mapY(v5);
        
        if (c1) c1.setAttribute('cy', y1);
        if (c2) c2.setAttribute('cy', y2);
        if (c3) c3.setAttribute('cy', y3);
        if (c4) c4.setAttribute('cy', y4);
        if (c5) c5.setAttribute('cy', y5);
        
        const d = `M 10 ${y1.toFixed(1)} Q 22.5 ${(y1 - 1).toFixed(1)} 35 ${y2.toFixed(1)} T 60 ${y3.toFixed(1)} T 80 ${y4.toFixed(1)} T 95 ${y5.toFixed(1)}`;
        pathEl.setAttribute('d', d);
    }

    function populateAnalyticsCameraDropdown() {
        const camSelect = document.getElementById('analytics-camera-select');
        if (camSelect) {
            const currentSelected = camSelect.value;
            camSelect.innerHTML = '<option value="all">Todas as Câmeras</option>';
            cameraList.forEach(cam => {
                const opt = document.createElement('option');
                opt.value = cam.name;
                opt.textContent = cam.name;
                if (cam.name === currentSelected) {
                    opt.selected = true;
                }
                camSelect.appendChild(opt);
            });
        }
    }
    window.populateAnalyticsCameraDropdown = populateAnalyticsCameraDropdown;

    function initHeatmapEngine() {
        btnToggleHeatmap.addEventListener('click', () => {
            isHeatmapActive = !isHeatmapActive;
            btnToggleHeatmap.classList.toggle('active');
            if (isHeatmapActive) {
                btnToggleHeatmap.innerText = "Calor Ativo";
            } else {
                btnToggleHeatmap.innerText = "Calor Oculto";
            }
            drawHeatmap();
        });

        btnResetHeatmap.addEventListener('click', () => {
            addLog('Limpando dados acumulados do mapa de calor de incidentes.');
            window.heatmapValues = { bebidas: 0, corr1: 0, caixas: 0, corr2: 0 };
            updateCorridorBarChartHTML(window.heatmapValues);
            drawHeatmap(true);
        });

        populateAnalyticsCameraDropdown();
        const camSelect = document.getElementById('analytics-camera-select');
        if (camSelect) {
            camSelect.addEventListener('change', () => {
                syncAnalyticsData();
            });
        }
    }

    function drawHeatmap(clear = false) {
        const ctx = heatmapCanvas.getContext('2d');
        const W = heatmapCanvas.width;
        const H = heatmapCanvas.height;

        ctx.fillStyle = '#070d19';
        ctx.fillRect(0, 0, W, H);

        // Draw blueprint walls and paths (Store blueprint design)
        ctx.strokeStyle = '#1b2d4b';
        ctx.lineWidth = 2;
        ctx.strokeRect(20, 20, W - 40, H - 40);

        // Draw Isles corridors labels
        ctx.fillStyle = '#111f38';
        // Aisle 1
        ctx.fillRect(60, 60, 160, 160);
        // Aisle 2
        ctx.fillRect(280, 60, 160, 160);
        // Liquor Zone
        ctx.fillRect(500, 60, 180, 120);
        // Checkout registers
        ctx.fillRect(120, 280, 80, 60);
        // Regs autoatendimento
        ctx.fillRect(240, 280, 80, 60);
        ctx.fillRect(360, 280, 80, 60);

        // Texts for departments
        ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.font = '10px var(--font-heading)';
        ctx.textAlign = 'center';
        ctx.fillText("CORREDOR 1 (Mercearia)", 140, 145);
        ctx.fillText("CORREDOR 2 (Biscoitos)", 360, 145);
        ctx.fillText("BEBIDAS FINAS (Adega)", 590, 120);
        ctx.fillText("CAIXA 1", 160, 315);
        ctx.fillText("CAIXA 2", 280, 315);
        ctx.fillText("AUTOATENDIMENTO", 400, 315);

        // Entrance
        ctx.strokeStyle = '#22d3ee';
        ctx.strokeRect(600, 320, 60, 5);
        ctx.fillStyle = '#22d3ee';
        ctx.font = 'bold 9px var(--font-body)';
        ctx.fillText("ENTRADA LOJA", 630, 345);

        // If clear mode, skip heat overlay
        if (clear) return;

        // If heatmap active, draw heat circular gradients representing incident counts
        if (isHeatmapActive) {
            const h = window.heatmapValues || { bebidas: 15, corr1: 10, caixas: 6, corr2: 3 };
            
            // Liquor Zone (RED)
            const rBebidas = Math.min(100, 50 + h.bebidas * 2.2);
            drawHeatCircle(ctx, 590, 120, rBebidas, 'rgba(255, 0, 85, 0.5)', 'rgba(255, 0, 85, 0)');
            
            // Aisle 1 (AMBER)
            const rCorr1 = Math.min(85, 40 + h.corr1 * 2.0);
            drawHeatCircle(ctx, 140, 120, rCorr1, 'rgba(255, 159, 0, 0.42)', 'rgba(255, 159, 0, 0)');
            
            // Checkout area (CYAN)
            const rCaixas = Math.min(90, 35 + h.caixas * 2.5);
            drawHeatCircle(ctx, 280, 310, rCaixas, 'rgba(0, 240, 255, 0.35)', 'rgba(0, 240, 255, 0)');
            
            // Aisle 2 (PURPLE)
            const rCorr2 = Math.min(80, 30 + h.corr2 * 3.0);
            drawHeatCircle(ctx, 360, 120, rCorr2, 'rgba(168, 85, 247, 0.32)', 'rgba(168, 85, 247, 0)');
        }
    }

    function drawHeatCircle(ctx, x, y, r, colorStart, colorEnd) {
        const grad = ctx.createRadialGradient(x, y, 5, x, y, r);
        grad.addColorStop(0, colorStart);
        grad.addColorStop(1, colorEnd);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
    }


    // --- TAB 3: CONNECT NEW CAMERA FORM ---
    
    // Tab switching for Camera Configuration Add Panel
    const tabSingleCamera = document.getElementById('tab-single-camera');
    const tabBatchDvr = document.getElementById('tab-batch-dvr');
    const singleFormContainer = document.getElementById('single-camera-form-container');
    const batchFormContainer = document.getElementById('batch-dvr-form-container');
    
    if (tabSingleCamera && tabBatchDvr) {
        tabSingleCamera.addEventListener('click', () => {
            tabSingleCamera.classList.add('active');
            tabBatchDvr.classList.remove('active');
            singleFormContainer.style.display = 'block';
            batchFormContainer.style.display = 'none';
        });
        
        tabBatchDvr.addEventListener('click', () => {
            tabBatchDvr.classList.add('active');
            tabSingleCamera.classList.remove('active');
            batchFormContainer.style.display = 'block';
            singleFormContainer.style.display = 'none';
        });
    }
    
    const dvrBrandSelect = document.getElementById('dvr-brand');
    const customUrlRow = document.getElementById('custom-url-row');
    if (dvrBrandSelect && customUrlRow) {
        dvrBrandSelect.addEventListener('change', () => {
            if (dvrBrandSelect.value === 'custom') {
                customUrlRow.style.display = 'block';
            } else {
                customUrlRow.style.display = 'none';
            }
        });
    }

    // Submit handler for Single Camera Form
    cameraAddForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const camName = document.getElementById('cam-name').value.trim();
        const camRtsp = document.getElementById('cam-rtsp').value.trim();
        const camDevice = document.getElementById('cam-device').value;
        const camProfile = document.getElementById('cam-profile').value;

        if (!camName || !camRtsp) {
            addLog('Preencha os campos obrigatórios para conectar a câmera.', 'error');
            return;
        }

        if (editingCameraId !== null) {
            // EDITING EXISTING CAMERA
            const cam = cameraList.find(c => c.id === editingCameraId);
            if (cam) {
                cam.name = camName;
                cam.rtsp = camRtsp;
                cam.device = camDevice;
                cam.profile = camProfile;
                cam.type = camName.toLowerCase().includes('caixa') ? 'checkout' : 'aisle';

                addLog(`[EDIÇÃO] Câmera "${camName}" atualizada com sucesso.`, 'success');
                
                // Update active camera title if currently active
                if (activeCameraId === cam.id) {
                    activeCamTitle.innerText = camName;
                    updateActiveStreams();
                }

                // Sync edit with database
                const tenantId = sessionStorage.getItem('aegiseye_tenant_id') || 'a7974ee4-329c-4c06-a57a-0377bcae242e';
                if (tenantId && cam.db_id) {
                    const payload = {
                        action: 'edit_camera',
                        id: cam.db_id,
                        tenant_id: tenantId,
                        name: camName,
                        device: camDevice || 'Dispositivo Genérico',
                        rtsp: camRtsp,
                        profile: camProfile,
                        type: cam.type,
                        status: cam.status
                    };
                    fetch('/api/configurar', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    })
                    .then(res => res.json())
                    .then(data => {
                        addLog(`[Sincronização] Alterações da câmera salvas no banco de dados.`, 'info');
                    })
                    .catch(err => {
                        console.error("Erro ao salvar alterações da câmera no banco:", err);
                    });
                }
            }
            cancelEditing();
        } else {
            // CREATING NEW CAMERA
            const newId = cameraList.length;
            const newCam = {
                id: newId,
                name: camName,
                status: "online",
                device: camDevice,
                rtsp: camRtsp,
                profile: camProfile,
                type: camName.toLowerCase().includes('caixa') ? 'checkout' : 'aisle'
            };

            cameraList.push(newCam);
            addLog(`[NOVA CÂMERA] Câmera "${camName}" conectada com sucesso no Edge Node via RTSP.`, 'success');
            
            if (cameraList.length === 1) {
                activeCameraId = 0;
                activeCamTitle.innerText = camName;
                updateActiveStreams();
            }

            const tenantId = sessionStorage.getItem('aegiseye_tenant_id') || 'a7974ee4-329c-4c06-a57a-0377bcae242e';
            if (tenantId) {
                const payload = {
                    action: 'add_camera',
                    tenant_id: tenantId,
                    name: camName,
                    device: camDevice || 'Dispositivo Genérico',
                    rtsp: camRtsp,
                    profile: camProfile,
                    type: newCam.type,
                    status: 'online'
                };
                fetch('/api/configurar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                .then(res => res.json())
                .then(data => {
                    addLog(`[Sincronização] Câmera salva no banco de dados.`, 'info');
                    const responseData = Array.isArray(data) ? data[0] : data;
                    if (responseData && responseData.id) {
                        newCam.db_id = responseData.id;
                    }
                })
                .catch(err => {
                    console.error("Erro de sincronização da câmera com o banco:", err);
                });
            }
            cameraAddForm.reset();
        }

        rebuildCameraGridHTML();
        rebuildCameraSelectorsHTML();
    });

    // Submit handler for Batch DVR Form
    const cameraBatchForm = document.getElementById('camera-batch-form');
    if (cameraBatchForm) {
        cameraBatchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const brand = document.getElementById('dvr-brand').value;
            const ip = document.getElementById('dvr-ip').value.trim();
            const port = document.getElementById('dvr-port').value.trim();
            const user = document.getElementById('dvr-user').value.trim();
            const pass = document.getElementById('dvr-pass').value.trim();
            const startCh = parseInt(document.getElementById('dvr-start-ch').value);
            const endCh = parseInt(document.getElementById('dvr-end-ch').value);
            const profile = document.getElementById('dvr-profile').value;
            const customPattern = document.getElementById('dvr-custom-pattern').value.trim();
            
            if (!ip || !port || !user || !pass || isNaN(startCh) || isNaN(endCh)) {
                addLog('Preencha todos os campos obrigatórios do DVR.', 'error');
                return;
            }
            
            if (startCh > endCh) {
                addLog('O canal inicial não pode ser maior que o canal final.', 'error');
                return;
            }
            
            const totalToImport = endCh - startCh + 1;
            addLog(`[DVR] Iniciando importação em lote de ${totalToImport} canais...`, 'info');
            
            const tenantId = sessionStorage.getItem('aegiseye_tenant_id');
            let completedCount = 0;
            
            for (let ch = startCh; ch <= endCh; ch++) {
                let rtspUrl = '';
                const encodedUser = encodeURIComponent(user);
                const encodedPass = encodeURIComponent(pass);
                
                if (brand === 'intelbras') {
                    rtspUrl = `rtsp://${encodedUser}:${encodedPass}@${ip}:${port}/cam/realmonitor?channel=${ch}&subtype=0`;
                } else if (brand === 'hikvision') {
                    rtspUrl = `rtsp://${encodedUser}:${encodedPass}@${ip}:${port}/Streaming/Channels/${ch}01`;
                } else if (brand === 'hikvision_av') {
                    rtspUrl = `rtsp://${encodedUser}:${encodedPass}@${ip}:${port}/h264/ch${ch}/main/av_stream`;
                } else if (brand === 'custom') {
                    rtspUrl = customPattern
                        .replace(/{channel}/g, ch)
                        .replace(/{ip}/g, ip)
                        .replace(/{port}/g, port)
                        .replace(/{user}/g, encodedUser)
                        .replace(/{pass}/g, encodedPass);
                }
                
                const camName = `Canal ${ch} - DVR (${brand.toUpperCase()})`;
                const newId = cameraList.length;
                const newCam = {
                    id: newId,
                    name: camName,
                    status: "online",
                    device: `DVR ${brand.toUpperCase()} - Canal ${ch}`,
                    rtsp: rtspUrl,
                    profile: profile,
                    type: 'aisle'
                };
                
                cameraList.push(newCam);
                
                if (tenantId) {
                    const payload = {
                        action: 'add_camera',
                        tenant_id: tenantId,
                        name: camName,
                        device: `DVR ${brand.toUpperCase()} - Canal ${ch}`,
                        rtsp: rtspUrl,
                        profile: profile,
                        type: 'aisle',
                        status: 'online'
                    };
                    
                    fetch('/api/configurar', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    })
                    .then(res => res.json())
                    .then(data => {
                        const responseData = Array.isArray(data) ? data[0] : data;
                        if (responseData && responseData.id) {
                            newCam.db_id = responseData.id;
                        }
                        completedCount++;
                        addLog(`[DVR] Canal ${ch} importado com sucesso para o banco.`, 'success');
                        if (completedCount === totalToImport) {
                            addLog(`[DVR] Sucesso! Todos os ${totalToImport} canais foram integrados.`, 'success');
                        }
                    })
                    .catch(err => {
                        console.error(`Erro ao salvar canal ${ch}:`, err);
                        addLog(`[DVR Erro] Falha ao importar Canal ${ch} no banco de dados.`, 'error');
                    });
                } else {
                    addLog(`[DVR Simulação] Canal ${ch} adicionado localmente.`, 'success');
                }
            }
            
            // Set first channel as active if camera list was previously empty
            if (cameraList.length === totalToImport) {
                activeCameraId = 0;
                const firstCam = cameraList[0];
                if (firstCam) {
                    activeCamTitle.innerText = firstCam.name;
                    updateActiveStreams();
                }
            }
            
            // Rebuild views with a small delay for DB sync
            setTimeout(() => {
                rebuildCameraGridHTML();
                rebuildCameraSelectorsHTML();
            }, 1000);
            
            cameraBatchForm.reset();
            if (customUrlRow) customUrlRow.style.display = 'none';
        });
    }

    function editCamera(id) {
        const cam = cameraList.find(c => c.id === id);
        if (!cam) return;

        editingCameraId = id;

        // Fill form fields
        document.getElementById('cam-name').value = cam.name;
        document.getElementById('cam-rtsp').value = cam.rtsp;
        document.getElementById('cam-device').value = cam.device;
        document.getElementById('cam-profile').value = cam.profile;

        // Change card title and button text
        const cardTitle = document.querySelector('.camera-add-card h3');
        if (cardTitle) cardTitle.innerText = 'Editar Câmera';

        const btnAdd = document.getElementById('btn-add-camera');
        if (btnAdd) {
            btnAdd.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Salvar Alterações`;
        }

        // Add a Cancelar button next to or below the submit button if it doesn't exist
        let cancelBtn = document.getElementById('btn-cancel-edit');
        if (!cancelBtn) {
            cancelBtn = document.createElement('button');
            cancelBtn.type = 'button';
            cancelBtn.id = 'btn-cancel-edit';
            cancelBtn.className = 'action-btn w-full btn-outline';
            cancelBtn.style.marginTop = '10px';
            cancelBtn.innerText = 'Cancelar Edição';
            cancelBtn.addEventListener('click', cancelEditing);
            document.getElementById('camera-add-form').appendChild(cancelBtn);
        }
    }

    function cancelEditing() {
        editingCameraId = null;
        document.getElementById('camera-add-form').reset();

        const cardTitle = document.querySelector('.camera-add-card h3');
        if (cardTitle) cardTitle.innerText = 'Adicionar Câmeras';

        const btnAdd = document.getElementById('btn-add-camera');
        if (btnAdd) {
            btnAdd.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> Conectar Câmera`;
        }

        const cancelBtn = document.getElementById('btn-cancel-edit');
        if (cancelBtn) cancelBtn.remove();
    }

    function rebuildCameraGridHTML() {
        cameraGrid.innerHTML = '';
        cameraTotalCountBadge.innerText = `${cameraList.length} Câmeras`;

        cameraList.forEach(cam => {
            const card = document.createElement('div');
            card.className = `camera-setup-card ${cam.status === 'warning' ? 'alert-active' : ''}`;
            
            const badgeClass = cam.status === 'online' ? 'online' : 'warning-badge';
            const badgeText = cam.status === 'online' ? 'Online' : 'Alerta';

            card.innerHTML = `
                <div class="camera-setup-header">
                    <div class="camera-setup-title-group">
                        <span class="camera-index">CAM-0${cam.id + 1}</span>
                        <h4>${cam.name}</h4>
                    </div>
                    <span class="badge-status ${badgeClass}">${badgeText}</span>
                </div>
                <div class="camera-setup-details">
                    <p><strong>URL RTSP:</strong> ${cam.rtsp}</p>
                    <p><strong>Dispositivo:</strong> ${cam.device}</p>
                    <p><strong>Modo IA:</strong> ${cam.profile}</p>
                </div>
                <div class="camera-setup-actions">
                    <button class="action-btn btn-sm btn-outline" data-edit-id="${cam.id}">Editar</button>
                    <button class="action-btn btn-sm btn-danger-outline" data-remove-id="${cam.id}">Remover</button>
                </div>
            `;
            cameraGrid.appendChild(card);
        });

        // Attach listeners for editing
        document.querySelectorAll('button[data-edit-id]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.getAttribute('data-edit-id'));
                editCamera(id);
            });
        });

        // Attach listeners for removal
        document.querySelectorAll('button[data-remove-id]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.getAttribute('data-remove-id'));
                removeCamera(id);
            });
        });
    }

    function removeCamera(id) {
        const idx = cameraList.findIndex(c => c.id === id);
        if (idx === -1) return;
        const cam = cameraList[idx];
        cameraList.splice(idx, 1);
        addLog(`Câmera "${cam.name}" desconectada e removida.`, 'warning');
        
        cameraList.forEach((c, i) => c.id = i);
        if (activeCameraId >= cameraList.length) {
            activeCameraId = Math.max(0, cameraList.length - 1);
        }

        rebuildCameraGridHTML();
        rebuildCameraSelectorsHTML();

        if (cam.db_id) {
            fetch('/api/configurar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'remove_camera', id: cam.db_id })
            })
            .then(res => {
                addLog(`[Sincronização] Câmera removida do banco de dados.`, 'info');
            })
            .catch(err => {
                console.error("Erro ao remover do banco de dados:", err);
            });
        }
    }

    function updateCameraStatusBadge(camId) {
        const camData = cameraList.find(c => c.id === camId) || cameraList[0];
        const statusIndicator = document.getElementById('camera-status-indicator');
        const statusDot = document.getElementById('camera-status-dot');
        const statusText = document.getElementById('camera-status-text');
        
        if (!camData) {
            if (statusIndicator) statusIndicator.style.display = 'none';
            return;
        }
        
        if (statusIndicator && statusDot && statusText) {
            statusIndicator.style.display = 'flex';
            const isOnline = camData.status === 'online';
            statusDot.style.backgroundColor = isOnline ? '#10b981' : '#ef4444';
            statusText.innerText = isOnline ? 'ONLINE' : 'OFFLINE (SIMULAÇÃO)';
        }
    }

    function rebuildCameraSelectorsHTML() {
        const dropdown = document.getElementById('camera-select-dropdown');
        if (!dropdown) return;
        dropdown.innerHTML = '';
        
        cameraList.forEach((cam) => {
            const opt = document.createElement('option');
            opt.value = cam.id;
            const emoji = cam.status === 'online' ? '🟢' : (cam.status === 'warning' ? '🟡' : '🔴');
            opt.innerText = `${emoji} ${cam.name}`;
            if (cam.id === activeCameraId && viewMode === 'single') {
                opt.selected = true;
            }
            dropdown.appendChild(opt);
        });
        
        updateCameraStatusBadge(activeCameraId);
        
        if (viewMode === 'grid') {
            rebuildVideoDisplayGridHTML();
        }
    }

    async function loadCamerasFromDatabase() {
        const tenantId = sessionStorage.getItem('aegiseye_tenant_id');
        if (!tenantId) return;
        
        try {
            const res = await fetch(`/api/get-cameras?tenant_id=${tenantId}`);
            if (res.ok) {
                const data = await res.json();
                if (data.success && Array.isArray(data.cameras)) {
                    cameraList = []; // Clean example cameras
                    if (data.cameras.length > 0) {
                        data.cameras.forEach((dbCam, idx) => {
                            cameraList.push({
                                id: idx,
                                db_id: dbCam.id,
                                name: dbCam.name,
                                device: dbCam.device || 'Dispositivo Genérico',
                                rtsp: dbCam.rtsp,
                                profile: dbCam.profile || 'Ocultamento / Suspeita',
                                type: dbCam.type || (dbCam.name.toLowerCase().includes('caixa') ? 'checkout' : 'aisle'),
                                status: dbCam.status || 'online'
                            });
                        });
                        
                        activeCameraId = 0;
                        const firstCam = cameraList[0];
                        if (firstCam) {
                            activeCamTitle.innerText = firstCam.name;
                            updateActiveStreams();
                        }
                    } else {
                        activeCamTitle.innerText = "Nenhuma câmera conectada";
                        cameraList.forEach(cam => {
                            if (cameraStreams[cam.id]) cameraStreams[cam.id].src = "";
                        });
                    }
                    
                    rebuildCameraGridHTML();
                    rebuildCameraSelectorsHTML();
                }
            }
        } catch(e) {
            console.error("Error loading cameras from database:", e);
        }
    }

    async function loadAlertsFromDatabase() {
        const tenantId = sessionStorage.getItem('aegiseye_tenant_id');
        const userId = sessionStorage.getItem('aegiseye_user_id');
        if (!tenantId) return;
        
        try {
            const url = userId ? `/api/get-alerts?tenant_id=${tenantId}&user_id=${userId}` : `/api/get-alerts?tenant_id=${tenantId}`;
            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                if (data.success && Array.isArray(data.alerts)) {
                    let updated = false;
                    data.alerts.forEach(dbAlert => {
                        const exists = alertsList.some(a => a.db_id === dbAlert.id);
                        if (!exists) {
                            const alertTime = dbAlert.timestamp ? new Date(dbAlert.timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : (dbAlert.time || new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }));
                            alertsList.unshift({
                                id: nextAlertId++,
                                db_id: dbAlert.id,
                                severity: dbAlert.severity,
                                time: alertTime,
                                timestamp: dbAlert.timestamp || null,
                                title: dbAlert.title,
                                camera: dbAlert.camera_name || dbAlert.camera || "Câmera Geral",
                                confidence: dbAlert.confidence || dbAlert.confidence_score || 90,
                                details: dbAlert.details || "Alerta detectado por processador IA local.",
                                trigger: dbAlert.trigger || dbAlert.risk_type || "Detecção automática.",
                                code: dbAlert.code || "DB_ALERT",
                                video_url: dbAlert.video_url || null
                            });
                            updated = true;
                            
                            // Play audio notification chime for new critical/warning alerts
                            if (dbAlert.severity === 'critical' || dbAlert.severity === 'warning') {
                                playNotificationSound();
                            }
                        }
                    });
                    if (updated || (alertsList.length > 0 && statsAlertsCount === 0) || statsAlertsCount !== data.today_count) {
                        statsAlertsCount = (data.today_count !== undefined) ? data.today_count : alertsList.length;
                        updateAlertsQueueHTML();
                        statsSavedValue = alertsList.filter(a => a.severity === 'critical').length * 250 + alertsList.filter(a => a.severity === 'warning').length * 100;
                        updateStatsHeader();
                    }
                }
            }
        } catch(e) {
            console.error("Error loading alerts from database:", e);
        }
    }

    rebuildCameraGridHTML();
    rebuildCameraSelectorsHTML();


    // --- TAB 4: SAAS & ROI CALCULATOR ENGINE ---
    function initSaaSCalculator() {
        saasCamerasSlider.addEventListener('input', () => { calculateROI(); });
        saasLossesSlider.addEventListener('input', () => { calculateROI(); });
        saasRateSlider.addEventListener('input', () => { calculateROI(); });
        saasModuleOps.addEventListener('change', () => { calculateROI(); });
        saasInfraCloud.addEventListener('change', () => { calculateROI(); });

        // Run calculation once
        calculateROI();
    }

    function calculateROI() {
        const cameras = parseInt(saasCamerasSlider.value);
        const losses = parseInt(saasLossesSlider.value);
        const rate = parseInt(saasRateSlider.value);
        const opsChecked = saasModuleOps.checked;
        const cloudChecked = saasInfraCloud.checked;

        // Update bubbles
        calcValCameras.innerText = `${cameras} câmeras`;
        calcValLosses.innerText = `R$ ${losses.toLocaleString('pt-BR')}`;
        calcValRate.innerText = `${rate}%`;

        // Calculate subscription SaaS fee based on standard commercial pricing structure
        let planPrice = 399;
        let planName = "Plano Bronze (Até 8 Câm.)";
        let tierId = "tier-bronze";

        if (cameras > 32) {
            planPrice = 2299;
            planName = "Plano Enterprise (64+ Câm.)";
            tierId = "tier-enterprise";
        } else if (cameras > 16) {
            planPrice = 1199;
            planName = "Plano Gold (Até 32 Câm.)";
            tierId = "tier-gold";
        } else if (cameras > 8) {
            planPrice = 599;
            planName = "Plano Silver (Até 16 Câm.)";
            tierId = "tier-silver";
        }

        // Add Operations Module fee if checked
        if (opsChecked) {
            planPrice += 199;
            planName += " + Ops Module";
        }

        // Highlight active plan card
        document.querySelectorAll('.tier-col').forEach(col => col.classList.remove('active'));
        const activeCard = document.getElementById(tierId);
        if (activeCard) activeCard.classList.add('active');

        // Calculate Hosting Cost
        let hostCost = 0;
        let hostDesc = "";
        if (cloudChecked) {
            hostCost = cameras * 25;
            hostDesc = `Nuvem GPU (R$ 25/cam)`;
        } else {
            hostCost = cameras * 10;
            hostDesc = `Edge Local (R$ 10/cam)`;
        }

        // Math equations
        // Ops module improves efficiency, increasing prevented losses by 15%
        const multiplier = opsChecked ? 1.15 : 1.0;
        const recovered = Math.round(losses * (rate / 100) * multiplier);
        const netSavings = recovered - planPrice - hostCost;
        const annualSavings = netSavings * 12;

        // Update UI results
        saasSubscriptionPrice.innerText = `R$ ${planPrice.toLocaleString('pt-BR')} / mês`;
        saasPlanName.innerText = planName;
        saasInfraCost.innerText = `R$ ${hostCost.toLocaleString('pt-BR')} / mês`;
        saasInfraDesc.innerText = hostDesc;
        saasRecoveredLosses.innerText = `R$ ${recovered.toLocaleString('pt-BR')} / mês`;
        
        if (netSavings > 0) {
            saasNetSavings.innerText = `R$ ${netSavings.toLocaleString('pt-BR')} / mês`;
            saasNetSavings.className = 'net-savings-value text-green';
            saasAnnualSavings.innerText = `Economia anual estimada para a loja: R$ ${annualSavings.toLocaleString('pt-BR')} / ano`;
        } else {
            saasNetSavings.innerText = `- R$ ${Math.abs(netSavings).toLocaleString('pt-BR')} / mês`;
            saasNetSavings.className = 'net-savings-value text-rose';
            saasAnnualSavings.innerText = `Ajuste os parâmetros. No cenário atual, o custo de implantação excede a economia calculada.`;
        }
    }

    // --- TAB 5: SETTINGS & PASSWORD SECURITY MODULE ---
    const settingsSubtabs = document.querySelectorAll('.settings-subtab');
    const settingsSections = document.querySelectorAll('.settings-section-content');
    const toast = document.getElementById('settings-toast');

    function showToast(msg, type = 'success') {
        if (!toast) return;
        toast.innerText = msg;
        toast.className = `settings-toast ${type}`;
        toast.style.display = 'block';
        setTimeout(() => {
            toast.style.display = 'none';
        }, 4000);
    }

    // Subtab switching
    settingsSubtabs.forEach(tab => {
        tab.addEventListener('click', () => {
            settingsSubtabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            const target = tab.getAttribute('data-subtab');
            settingsSections.forEach(sec => {
                sec.style.display = 'none';
                if (sec.id === `subtab-${target}`) {
                    sec.style.display = 'block';
                }
            });
        });
    });

    // AI Settings inputs
    const sensRange = document.getElementById('settings-ai-sensitivity');
    const sensVal = document.getElementById('ai-sensitivity-val');
    const fpsRange = document.getElementById('settings-ai-fps');
    const fpsVal = document.getElementById('ai-fps-val');

    if (sensRange && sensVal) {
        sensRange.addEventListener('input', (e) => {
            sensVal.innerText = `${e.target.value}%`;
        });
    }
    if (fpsRange && fpsVal) {
        fpsRange.addEventListener('input', (e) => {
            fpsVal.innerText = `${e.target.value} FPS`;
        });
    }

    // Load Settings
    async function loadSettings() {
        const tenantId = sessionStorage.getItem('aegiseye_tenant_id');
        if (!tenantId) return;
        try {
            const res = await fetch(`/api/get-settings?tenant_id=${tenantId}`);
            if (res.ok) {
                const data = await res.json();
                if (data.success) {
                    if (document.getElementById('settings-webhook-url')) {
                        document.getElementById('settings-webhook-url').value = data.n8n_webhook_url || '';
                    }
                    if (document.getElementById('settings-master-key')) {
                        document.getElementById('settings-master-key').value = data.recovery_master_key || '';
                    }
                    if (sensRange && sensVal) {
                        sensRange.value = data.ai_sensitivity || 75;
                        sensVal.innerText = `${sensRange.value}%`;
                    }
                    if (fpsRange && fpsVal) {
                        fpsRange.value = data.ai_fps || 10;
                        fpsVal.innerText = `${fpsRange.value} FPS`;
                    }
                }
            }
        } catch (e) {
            console.error("Erro ao carregar configurações:", e);
        }
    }

    // Password strength check
    const newPassInput = document.getElementById('settings-new-password');
    const strengthBar = document.getElementById('strength-bar');
    const strengthText = document.getElementById('strength-text');
    const reqLength = document.getElementById('req-length');
    const reqCase = document.getElementById('req-case');
    const reqNumber = document.getElementById('req-number');
    const reqSpecial = document.getElementById('req-special');

    if (newPassInput) {
        newPassInput.addEventListener('input', () => {
            const val = newPassInput.value;
            let score = 0;
            
            // Length
            const hasLength = val.length >= 8;
            if (hasLength) { score++; reqLength.className = 'req-item valid'; }
            else { reqLength.className = 'req-item invalid'; }
            
            // Case
            const hasCase = /[a-z]/.test(val) && /[A-Z]/.test(val);
            if (hasCase) { score++; reqCase.className = 'req-item valid'; }
            else { reqCase.className = 'req-item invalid'; }
            
            // Number
            const hasNumber = /[0-9]/.test(val);
            if (hasNumber) { score++; reqNumber.className = 'req-item valid'; }
            else { reqNumber.className = 'req-item invalid'; }
            
            // Special
            const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(val);
            if (hasSpecial) { score++; reqSpecial.className = 'req-item valid'; }
            else { reqSpecial.className = 'req-item invalid'; }
            
            // Render UI
            if (val === '') {
                strengthBar.style.width = '0%';
                strengthText.innerText = 'Força: -';
            } else if (score <= 1) {
                strengthBar.style.width = '25%';
                strengthBar.style.backgroundColor = 'var(--rose-500)';
                strengthText.innerText = 'Força: Fraca';
            } else if (score <= 3) {
                strengthBar.style.width = '60%';
                strengthBar.style.backgroundColor = 'var(--amber-500)';
                strengthText.innerText = 'Força: Média';
            } else {
                strengthBar.style.width = '100%';
                strengthBar.style.backgroundColor = 'var(--green-500)';
                strengthText.innerText = 'Força: Forte';
            }
        });
    }

    // Submit general settings
    const generalForm = document.getElementById('form-settings-general');
    if (generalForm) {
        generalForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const tenantId = sessionStorage.getItem('aegiseye_tenant_id');
            const webhookUrl = document.getElementById('settings-webhook-url').value.trim();
            const masterKey = document.getElementById('settings-master-key') ? document.getElementById('settings-master-key').value.trim() : 'AEGISEYE_MASTER_KEY_2026';
            
            try {
                const res = await fetch('/api/save-settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tenant_id: tenantId,
                        n8n_webhook_url: webhookUrl,
                        recovery_master_key: masterKey,
                        ai_sensitivity: sensRange ? parseInt(sensRange.value) : 75,
                        ai_fps: fpsRange ? parseInt(fpsRange.value) : 10
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Configurações salvas com sucesso!");
                } else {
                    showToast(data.message || "Erro ao salvar.", "error");
                }
            } catch (err) {
                showToast("Erro na conexão com o servidor.", "error");
            }
        });
    }

    // Submit AI settings
    const aiForm = document.getElementById('form-settings-ai');
    if (aiForm) {
        aiForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const tenantId = sessionStorage.getItem('aegiseye_tenant_id');
            const webhookUrl = document.getElementById('settings-webhook-url') ? document.getElementById('settings-webhook-url').value.trim() : '';
            const masterKey = document.getElementById('settings-master-key') ? document.getElementById('settings-master-key').value.trim() : 'AEGISEYE_MASTER_KEY_2026';
            
            try {
                const res = await fetch('/api/save-settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tenant_id: tenantId,
                        n8n_webhook_url: webhookUrl,
                        recovery_master_key: masterKey,
                        ai_sensitivity: parseInt(sensRange.value),
                        ai_fps: parseInt(fpsRange.value)
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Configurações salvas com sucesso!");
                } else {
                    showToast(data.message || "Erro ao salvar.", "error");
                }
            } catch (err) {
                showToast("Erro na conexão com o servidor.", "error");
            }
        });
    }

    // Submit Security (Reset Password & Master Key)
    const securityForm = document.getElementById('form-settings-security');
    if (securityForm) {
        securityForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userId = sessionStorage.getItem('aegiseye_user_id');
            const tenantId = sessionStorage.getItem('aegiseye_tenant_id');
            const currentPass = document.getElementById('settings-current-password').value;
            const newPass = newPassInput.value;
            const masterKey = document.getElementById('settings-master-key').value.trim();

            // Validate strength first
            const hasLength = newPass.length >= 8;
            const hasCase = /[a-z]/.test(newPass) && /[A-Z]/.test(newPass);
            const hasNumber = /[0-9]/.test(newPass);
            const hasSpecial = /[!@#$%^&*(),.?\":{}|<>]/.test(newPass);

            if (!hasLength || !hasCase || !hasNumber || !hasSpecial) {
                showToast("A nova senha não atende a todos os requisitos mínimos de força.", "error");
                return;
            }

            try {
                // 1. Reset password
                const resPass = await fetch('/api/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        current_password: currentPass,
                        new_password: newPass
                    })
                });
                const dataPass = await resPass.json();
                if (!dataPass.success) {
                    showToast(dataPass.message || "Senha atual incorreta.", "error");
                    return;
                }

                // 2. Save master key
                const webhookUrl = document.getElementById('settings-webhook-url') ? document.getElementById('settings-webhook-url').value.trim() : '';
                await fetch('/api/save-settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tenant_id: tenantId,
                        n8n_webhook_url: webhookUrl,
                        recovery_master_key: masterKey,
                        ai_sensitivity: sensRange ? parseInt(sensRange.value) : 75,
                        ai_fps: fpsRange ? parseInt(fpsRange.value) : 10
                    })
                });

                showToast("Configurações salvas com sucesso!");
                document.getElementById('settings-current-password').value = '';
                newPassInput.value = '';
                strengthBar.style.width = '0%';
                strengthText.innerText = 'Força: -';
                document.querySelectorAll('.req-item').forEach(li => li.className = 'req-item invalid');
            } catch (err) {
                showToast("Erro na comunicação com o servidor.", "error");
            }
        });
    }

    // Expose loadSettings globally so navigation click triggers it
    window.loadSettings = loadSettings;
});
