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
    
    // Map of camera stream images
    const cameraStreams = {};

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
                    const streamUrl = `http://${window.location.hostname}:8082/stream?rtsp=${encodeURIComponent(cam.rtsp)}`;
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
    const btnTriggerSuspicious = document.getElementById('btn-trigger-suspicious');
    const simTypeSelector = document.getElementById('sim-type-selector');
    const sensitivitySlider = document.getElementById('sensitivity-slider');
    const sensitivityVal = document.getElementById('sensitivity-val');
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
        try {
            const res = await fetch(`/api/edge-status?tenant_id=${tenantId}`);
            if (res.ok) {
                const data = await res.json();
                isEdgeOnline = data.online;
                updateActiveStreams();
                
                const dot = document.querySelector('.pulse-dot');
                const text = document.querySelector('.status-text');
                if (dot && text) {
                    if (data.online) {
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
        } catch (e) {
            console.error("Error fetching edge status:", e);
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
                setTimeout(drawHeatmap, 50); // Redraw heatmap canvas when tab shown
            } else if (targetTab === 'cameras') {
                viewTitle.innerText = "Gerenciar Câmeras";
                viewSubtitle.innerText = "Configuração de conexões RTSP locais e inteligência por câmera";
            } else if (targetTab === 'saas') {
                viewTitle.innerText = "Simulador SaaS & ROI";
                viewSubtitle.innerText = "Simule e entenda a viabilidade comercial do projeto AegisEye AI";
            }
        });
    });

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
        activeAlertBadge.innerText = `${alertsList.length} ativos`;
        
        if (alertsList.length === 0) {
            alertsQueueContainer.innerHTML = `
                <div class="empty-alerts-notice" style="text-align: center; padding: 40px 20px; color: var(--slate-600); border: 1px dashed var(--slate-800); border-radius: var(--radius-md);">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 32px; height: 32px; margin-bottom: 8px; opacity: 0.5;"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/></svg>
                    <p>Nenhum alerta pendente</p>
                </div>
            `;
            return;
        }

        alertsList.forEach(alert => {
            const card = document.createElement('div');
            card.className = `alert-card ${alert.severity} ${alert.id === 1 ? 'anim-pulse-card' : ''}`;
            card.setAttribute('data-alert-id', alert.id);

            const labelSeverity = alert.severity === 'critical' ? 'Crítico' : (alert.severity === 'warning' ? 'Atenção' : 'Médio');
            const confClass = alert.severity === 'critical' ? 'text-rose' : (alert.severity === 'warning' ? 'text-amber' : 'text-cyan');

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
                <div class="alert-card-actions">
                    <div class="alert-feedback-btns">
                        <button class="btn-feedback correct" title="Confirmar Alerta" data-alert-id="${alert.id}">✓</button>
                        <button class="btn-feedback incorrect" title="Falso Positivo" data-alert-id="${alert.id}">✗</button>
                    </div>
                </div>
            `;
            alertsQueueContainer.appendChild(card);
        });

        document.querySelectorAll('.btn-feedback.correct').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.getAttribute('data-alert-id'));
                handleAlertFeedback(id, true);
            });
        });

        document.querySelectorAll('.btn-feedback.incorrect').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.getAttribute('data-alert-id'));
                handleAlertFeedback(id, false);
            });
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
            updateActiveStreams();
            rebuildCameraSelectorsHTML();
            
            isSuspiciousActive = false;
            suspiciousPhase = 0;
            detectionNotice.classList.remove('active');
            detectionNotice.innerText = "Nenhuma atividade suspeita no momento";
            
            addLog(`Visualizando fluxo em tempo real: ${camData.name} (${camData.device}).`);
        });
    }

    sensitivitySlider.addEventListener('input', (e) => {
        sensitivityVal.innerText = `${e.target.value}%`;
    });

    btnTriggerSuspicious.addEventListener('click', () => {
        if (isSuspiciousActive) {
            addLog('A simulação já está em andamento nesta câmera.', 'warning');
            return;
        }
        isSuspiciousActive = true;
        suspiciousPhase = 0;
        liveFrame = 0;
        addLog(`Iniciando simulação de comportamento suspeito na câmera: ${cameraList[activeCameraId].name}.`, 'warning');
    });

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
                            ctx.fillText("MODO DE EDIÇÃO DO MAPA DA LOJA - ARRASTE E REDIMENSIONE AS GÔNDOLAS E CAIXAS", W/2, 19);
                            ctx.textAlign = 'start';
                        }
                    }

                    // Handle Normal / Suspicious Simulation
                    if (!isSuspiciousActive) {
                        const cycle = (liveFrame % 300) / 300;
                        let px = W/2 + Math.sin(cycle * Math.PI * 2) * 100;
                        let py = H/2 + Math.cos(cycle * Math.PI * 2) * 40 + 50;

                        drawTrackObject(ctx, px, py, 120, "Pessoa #187", '#00f0ff');
                        detectionNotice.classList.remove('active');
                        detectionNotice.innerText = "Nenhuma atividade suspeita no momento";
                    } else {
                        const simType = simTypeSelector.value;
                        const timeline = liveFrame % 380;
                        
                        if (simType === 'concealment') {
                            let px = W / 2, py = H - 50, actionState = 'walk';
                            const targetShelf = mapElements.find(item => item.type === 'shelf');
                            let targetX = 320, targetY = 220;
                            if (targetShelf) {
                                targetX = targetShelf.x + targetShelf.w + 40;
                                targetY = targetShelf.y + targetShelf.h / 2;
                            } else {
                                const targetCheckout = mapElements.find(item => item.type === 'checkout_counter');
                                if (targetCheckout) {
                                    targetX = targetCheckout.x + targetCheckout.w / 2;
                                    targetY = targetCheckout.y - 40;
                                }
                            }

                            if (timeline < 100) {
                                px = W/2 - (W/2 - targetX) * (timeline / 100);
                                py = H - 50 - (H - 50 - targetY) * (timeline / 100);
                            } else if (timeline < 220) {
                                px = targetX; py = targetY; actionState = 'reach';
                            } else if (timeline < 300) {
                                px = targetX; py = targetY; actionState = 'conceal';
                            } else {
                                px = targetX + (W/2 - targetX) * ((timeline - 300) / 80);
                                py = targetY + (H - 50 - targetY) * ((timeline - 300) / 80);
                                actionState = 'leave';
                            }

                            let trackColor = '#00f0ff';
                            if (actionState === 'reach') {
                                trackColor = '#ff9f00';
                                detectionNotice.classList.remove('active');
                                detectionNotice.innerText = "[ALERTA INTERNO] Tempo de permanência na seção cara elevado";
                            } else if (actionState === 'conceal') {
                                trackColor = '#ff0055';
                                detectionNotice.classList.add('active');
                                detectionNotice.innerText = `⚠ ALERTA CRÍTICO: Ocultamento suspeito de objeto (Confiança: 89%)`;
                                if (timeline === 225) triggerNewAlert("concealment");
                            } else if (actionState === 'leave') {
                                trackColor = '#ff0055';
                            }
                            drawTrackObject(ctx, px, py, 110, "Pessoa #194", trackColor, actionState);

                        } else if (simType === 'lingering') {
                            const targetShelf = mapElements.find(item => item.type === 'shelf');
                            let px = 320, py = 220;
                            if (targetShelf) {
                                px = targetShelf.x + targetShelf.w + 40;
                                py = targetShelf.y + targetShelf.h / 2;
                            } else {
                                const targetCheckout = mapElements.find(item => item.type === 'checkout_counter');
                                if (targetCheckout) {
                                    px = targetCheckout.x + targetCheckout.w / 2;
                                    py = targetCheckout.y - 40;
                                }
                            }
                            
                            let trackColor = '#00f0ff';
                            let label = "Pessoa #199";

                            if (timeline > 120) {
                                trackColor = '#ff9f00';
                                detectionNotice.classList.add('active');
                                detectionNotice.innerText = `⚠ ALERTA: Tempo de permanência anormal na adega: ${Math.round(timeline/10)}s`;
                                if (timeline === 200) triggerNewAlert("lingering");
                            }
                            drawTrackObject(ctx, px, py, 110, label, trackColor, 'stand');

                        } else if (simType === 'running') {
                            let px = 50 + (timeline / 380) * (W - 100);
                            let py = H/2 + 50;
                            let trackColor = '#ff0055';
                            detectionNotice.classList.add('active');
                            detectionNotice.innerText = `⚠ ALERTA CRÍTICO: Pessoa correndo no corredor (Velocidade Anormal)`;
                            if (timeline === 100) triggerNewAlert("running");
                            drawTrackObject(ctx, px, py, 110, "Pessoa #205", trackColor, 'run');

                        } else if (simType === 'fall') {
                            let px = W/2;
                            let py = H/2 + 80;
                            let trackColor = '#ff9f00';

                            if (timeline < 120) {
                                px = W/2 - 80 + timeline*0.8;
                                drawTrackObject(ctx, px, py, 110, "Pessoa #211", '#00f0ff', 'walk');
                            } else {
                                trackColor = '#ff0055';
                                detectionNotice.classList.add('active');
                                detectionNotice.innerText = `⚠ ALERTA DE EMERGÊNCIA: Queda de cliente detectada no Corredor 2`;
                                if (timeline === 125) triggerNewAlert("fall");
                                
                                ctx.strokeStyle = trackColor;
                                ctx.lineWidth = 2;
                                ctx.strokeRect(px - 60, py - 10, 120, 40);
                                ctx.fillStyle = trackColor;
                                ctx.fillRect(px - 60, py - 30, 90, 20);
                                ctx.fillStyle = '#000';
                                ctx.font = 'bold 9px monospace';
                                ctx.fillText("Queda #211 (94%)", px - 56, py - 16);
                                
                                ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
                                ctx.lineWidth = 1;
                                ctx.beginPath(); ctx.arc(px - 40, py + 10, 5, 0, Math.PI*2); ctx.stroke();
                                ctx.beginPath(); ctx.moveTo(px - 35, py + 10); ctx.lineTo(px + 20, py + 10); ctx.stroke();
                            }

                        } else if (simType === 'shelf') {
                            const targetShelf = mapElements.find(item => item.type === 'shelf');
                            let sx = 110, sy = 160, sw = 140, sh = 60;
                            if (targetShelf) {
                                sx = targetShelf.x + targetShelf.w * 0.1;
                                sy = targetShelf.y + targetShelf.h * 0.3;
                                sw = targetShelf.w * 0.8;
                                sh = targetShelf.h * 0.2;
                            }
                            
                            detectionNotice.classList.add('active');
                            detectionNotice.innerText = `⚠ OPERACIONAL: Gôndola vazia detectada no Corredor 1 (Nível 2)`;
                            if (timeline === 100) triggerNewAlert("shelf");

                            ctx.strokeStyle = '#ff9f00';
                            ctx.lineWidth = 1.5;
                            ctx.setLineDash([4, 4]);
                            ctx.strokeRect(sx, sy, sw, sh);
                            ctx.setLineDash([]);
                            
                            ctx.fillStyle = 'rgba(255, 159, 0, 0.2)';
                            ctx.fillRect(sx, sy, sw, sh);

                            ctx.fillStyle = '#ff9f00';
                            ctx.fillRect(sx, sy - 18, 110, 18);
                            ctx.fillStyle = '#000';
                            ctx.font = 'bold 9px monospace';
                            ctx.fillText("Gôndola Vazia (87%)", sx + 4, sy - 6);
                        }
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
                        
                        // If simulation active on this specific camera, draw bounding box
                        if (isSuspiciousActive && cam.id === activeCameraId) {
                            gCtx.strokeStyle = '#ff0055';
                            gCtx.lineWidth = 1.5;
                            gCtx.strokeRect(gW/3, gH/3, gW/3, gH/3);
                            gCtx.fillStyle = '#ff0055';
                            gCtx.fillRect(gW/3, gH/3 - 12, 60, 12);
                            gCtx.fillStyle = '#000';
                            gCtx.font = 'bold 7px sans-serif';
                            gCtx.fillText("SUSPEITA", gW/3 + 3, gH/3 - 3);
                        }
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

    function drawTrackObject(ctx, x, y, size, label, color, action = 'walk') {
        const w = size / 2.2;
        const h = size;

        // Draw bounding box
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x - w/2, y - h/2, w, h);

        // Bounding box label
        ctx.fillStyle = color;
        ctx.fillRect(x - w/2, y - h/2 - 16, w + 10, 16);
        ctx.fillStyle = '#000';
        ctx.font = 'bold 9px monospace';
        ctx.fillText(label, x - w/2 + 4, y - h/2 - 4);

        // Draw pose skeleton (visualize behavioral triggers)
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.lineWidth = 1;
        // Head
        ctx.beginPath(); ctx.arc(x, y - h/2 + 15, 6, 0, Math.PI * 2); ctx.stroke();
        // Torso
        ctx.beginPath(); ctx.moveTo(x, y - h/2 + 21); ctx.lineTo(x, y + 10); ctx.stroke();
        // Shoulders
        ctx.beginPath(); ctx.moveTo(x - 12, y - h/2 + 25); ctx.lineTo(x + 12, y - h/2 + 25); ctx.stroke();
        // Arms
        ctx.beginPath(); ctx.moveTo(x - 12, y - h/2 + 25);
        if (action === 'reach') {
            ctx.lineTo(x - 25, y - 5); ctx.lineTo(x - 45, y - 20); // reaching shelf
        } else if (action === 'conceal') {
            ctx.lineTo(x - 15, y - 5); ctx.lineTo(x - 2, y + 8); // moving item under jacket
        } else if (action === 'run') {
            ctx.lineTo(x - 5, y - 10); ctx.lineTo(x - 25, y - 20); // running arm swing
        } else if (action === 'stand') {
            ctx.lineTo(x - 15, y - 5); ctx.lineTo(x - 15, y + 15); // hanging straight down
        } else {
            ctx.lineTo(x - 18, y + 5); ctx.lineTo(x - 12, y + 20); // normal swinging
        }
        ctx.stroke();

        ctx.beginPath(); ctx.moveTo(x + 12, y - h/2 + 25); ctx.lineTo(x + 18, y + 5); ctx.lineTo(x + 12, y + 20); ctx.stroke();
        
        // Legs
        ctx.beginPath(); ctx.moveTo(x, y + 10); ctx.lineTo(x - 8, y + h/2); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x, y + 10); ctx.lineTo(x + 8, y + h/2); ctx.stroke();
    }

    function triggerNewAlert(type = "concealment") {
        const camData = cameraList[activeCameraId];
        let title = "Ação suspeita detectada";
        let details = "Comportamento incomum monitorado.";
        let severity = "critical";
        let confidence = 85;
        let trigger = "Pipeline disparado.";
        let code = "SUSPICIOUS_GENERIC";

        if (type === "concealment") {
            title = "Remoção e ocultação rápida";
            details = "Cliente removeu garrafa de whisky e ocultou sob bolso interno.";
            severity = "critical";
            confidence = Math.round(82 + Math.random() * 12);
            trigger = "YOLO detectou produto -> ByteTrack vinculou track a Pessoa #194 -> Segmentação de pose detectou braço inserindo item sob jaqueta.";
            code = "CONCEALMENT_FAST";
        } else if (type === "lingering") {
            title = "Permanência alta na adega";
            details = "Cliente parado na zona de risco por mais de 3 minutos.";
            severity = "warning";
            confidence = Math.round(85 + Math.random() * 10);
            trigger = "Objeto de interesse (Adega) monitorado -> track parado na zona de exclusão por mais de 180s.";
            code = "LINGERING_HIGH";
        } else if (type === "running") {
            title = "Pessoa correndo no corredor";
            details = "Pessoa correndo no corredor de biscoitos em velocidade anormal.";
            severity = "critical";
            confidence = Math.round(90 + Math.random() * 8);
            trigger = "Vetor de deslocamento do track ID #205 excedeu 3.5 m/s em zona interna da loja.";
            code = "SPEED_ABNORMAL";
        } else if (type === "fall") {
            title = "Queda de cliente detectada";
            details = "Emergência: Sensor de pose detectou cliente caído no chão do Corredor 2.";
            severity = "critical";
            confidence = Math.round(92 + Math.random() * 6);
            trigger = "Pose estimation: Keypoints de ombros e quadril alinhados horizontalmente a < 20cm do nível do chão.";
            code = "CUSTOMER_FALL";
        } else if (type === "shelf") {
            title = "Reposição de gôndola necessária";
            details = "Operação: Nível de preenchimento da prateleira de molhos caiu abaixo de 20%.";
            severity = "medium";
            confidence = Math.round(80 + Math.random() * 10);
            trigger = "Segmentação semântica: Área de prateleira mapeada como vazia excede 80% do ROI demarcado.";
            code = "SHELF_EMPTY";
        }

        // Avoid duplicate alerts in the queue
        const isDuplicate = alertsList.some(a => a.code === code && a.camera === camData.name);
        if (isDuplicate) return;

        const newAlert = {
            id: nextAlertId,
            severity: severity,
            time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
            title: title,
            details: details,
            camera: camData.name,
            confidence: confidence,
            trigger: trigger,
            code: code
        };

        // Add to front of alerts list
        alertsList.unshift(newAlert);
        nextAlertId++;
        
        // Update alerts layout
        updateAlertsQueueHTML();
        addLog(`[ALERTA DE EVENTO] Nova ocorrência: "${title}" na câmera "${camData.name}" - Confiança: ${confidence}%`, severity === 'critical' ? 'error' : (severity === 'warning' ? 'warning' : 'info'));
        
        // Push alert badge notification
        const badge = document.getElementById('active-alert-badge');
        badge.classList.add('critical');
        setTimeout(() => badge.classList.remove('critical'), 1000);
    }


    // --- TAB 2: STORE HEATMAP ENGINE ---
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
            // Draw empty store layout
            drawHeatmap(true);
        });
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
            // Liquor Zone (Most critical area, RED)
            drawHeatCircle(ctx, 590, 100, 80, 'rgba(255, 0, 85, 0.5)', 'rgba(255, 0, 85, 0)');
            // Aisle 1 (Medium, AMBER)
            drawHeatCircle(ctx, 140, 100, 60, 'rgba(255, 159, 0, 0.4)', 'rgba(255, 159, 0, 0)');
            // Checkout area (Low-Medium, CYAN)
            drawHeatCircle(ctx, 280, 300, 50, 'rgba(0, 240, 255, 0.35)', 'rgba(0, 240, 255, 0)');
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

        rebuildCameraGridHTML();
        rebuildCameraSelectorsHTML();

        const tenantId = sessionStorage.getItem('aegiseye_tenant_id');
        if (tenantId) {
            const payload = {
                action: 'add_camera',
                tenant_id: tenantId,
                name: camName,
                device: camDevice || 'Dispositivo Genérico',
                rtsp: camRtsp,
                profile: camProfile,
                type: camName.toLowerCase().includes('caixa') ? 'checkout' : 'aisle',
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
                if (brand === 'intelbras') {
                    rtspUrl = `rtsp://${user}:${pass}@${ip}:${port}/cam/realmonitor?channel=${ch}&subtype=0`;
                } else if (brand === 'hikvision') {
                    rtspUrl = `rtsp://${user}:${pass}@${ip}:${port}/Streaming/Channels/${ch}01`;
                } else if (brand === 'hikvision_av') {
                    rtspUrl = `rtsp://${user}:${pass}@${ip}:${port}/h264/ch${ch}/main/av_stream`;
                } else if (brand === 'custom') {
                    rtspUrl = customPattern
                        .replace(/{channel}/g, ch)
                        .replace(/{ip}/g, ip)
                        .replace(/{port}/g, port)
                        .replace(/{user}/g, user)
                        .replace(/{pass}/g, pass);
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
                    <button class="action-btn btn-sm btn-outline">Editar</button>
                    <button class="action-btn btn-sm btn-danger-outline" data-remove-id="${cam.id}">Remover</button>
                </div>
            `;
            cameraGrid.appendChild(card);
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
        if (!tenantId) return;
        
        try {
            const res = await fetch(`/api/get-alerts?tenant_id=${tenantId}`);
            if (res.ok) {
                const data = await res.json();
                if (data.success && Array.isArray(data.alerts)) {
                    let updated = false;
                    data.alerts.forEach(dbAlert => {
                        const exists = alertsList.some(a => a.db_id === dbAlert.id || (a.title === dbAlert.title && a.time === dbAlert.time));
                        if (!exists) {
                            alertsList.unshift({
                                id: nextAlertId++,
                                db_id: dbAlert.id,
                                severity: dbAlert.severity,
                                time: dbAlert.time,
                                title: dbAlert.title,
                                camera: dbAlert.camera,
                                confidence: dbAlert.confidence,
                                details: dbAlert.details || "Alerta detectado por processador IA local.",
                                trigger: dbAlert.trigger || "Detecção automática.",
                                code: dbAlert.code || "DB_ALERT"
                            });
                            updated = true;
                        }
                    });
                    if (updated || (alertsList.length > 0 && statsAlertsCount === 0)) {
                        updateAlertsQueueHTML();
                        statsAlertsCount = alertsList.length;
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
});
