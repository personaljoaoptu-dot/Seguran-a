// --- AEGISEYE AI - INTERACTIVE SYSTEM ENGINE ---

document.addEventListener('DOMContentLoaded', () => {
    // --- STATE MANAGEMENT & VARIABLES ---
    let activeTab = 'live';
    let activeCameraId = 0;
    let liveAnimId = null;
    let liveFrame = 0;
    let isSuspiciousActive = false;
    let suspiciousPhase = 0; // 0: enter, 1: browse, 2: conceal, 3: exit
    let modalAnimId = null;
    let modalFrame = 0;
    let currentModalAlert = null;
    let isHeatmapActive = true;
    let statsAlertsCount = 24;
    let statsSavedValue = 4250;
    let nextAlertId = 4;

    let cameraList = [
        { id: 0, name: "Corredor 1 (Mercearia)", status: "online", device: "Intelbras VIP 3230 B", rtsp: "rtsp://192.168.1.100/ch1", profile: "Ocultamento / Suspeita", type: "aisle" },
        { id: 1, name: "Corredor 2 (Biscoitos)", status: "online", device: "Dahua HDW1230S", rtsp: "rtsp://192.168.1.100/ch2", profile: "Ocultamento / Fluxo de Pessoas", type: "aisle" },
        { id: 2, name: "Bebidas Finas", status: "warning", device: "Hikvision DS-2CD2021G1", rtsp: "rtsp://192.168.1.100/ch3", profile: "Permanência Alta / Ocultamento", type: "liquor" },
        { id: 3, name: "Caixa 1", status: "online", device: "Hikvision DS-2CD1023G0", rtsp: "rtsp://192.168.1.100/ch4", profile: "Desistência / Fila Larga", type: "checkout" },
        { id: 4, name: "Caixa 2 (Autoatendimento)", status: "online", device: "Intelbras VIP 1230 D", rtsp: "rtsp://192.168.1.100/ch5", profile: "Checkout Não Escaneado", type: "checkout" }
    ];

    let alertsList = [
        { id: 1, severity: "critical", time: "14:51", title: "Produto escondido sob a roupa", details: "Objeto retirado da prateleira e ocultado na jaqueta.", camera: "Bebidas Finas", confidence: 84, trigger: "Objeto retirado de prateleira -> movimento rápido para o bolso interno da jaqueta.", code: "CONCEALMENT_JACKET" },
        { id: 2, severity: "warning", time: "14:40", title: "Permanência prolongada na seção", details: "Cliente parado na zona de risco de bebidas finas há mais de 12 minutos.", camera: "Bebidas Finas", confidence: 95, trigger: "Objeto de interesse (bebida cara) monitorado -> track parado na zona de exclusão por 750s.", code: "LIGERING_WARN" },
        { id: 3, severity: "medium", time: "14:32", title: "Objeto colocado em mochila", details: "Objeto retirado de prateleira inserido em mochila de costas.", camera: "Corredor 1 (Mercearia)", confidence: 91, trigger: "Mão alcançou prateleira -> objeto retirado -> mão interceptou mochila -> objeto oculto.", code: "CONCEALMENT_BAG" }
    ];

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

    // Modal elements
    const videoModal = document.getElementById('video-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const modalVideoCanvas = document.getElementById('modal-video-canvas');
    const modalDetectionText = document.getElementById('modal-detection-text');
    const modalMetaCamera = document.getElementById('modal-meta-camera');
    const modalMetaTime = document.getElementById('modal-meta-time');
    const modalMetaTrigger = document.getElementById('modal-meta-trigger');
    const btnModalFeedbackCorrect = document.getElementById('btn-modal-feedback-correct');
    const btnModalFeedbackIncorrect = document.getElementById('btn-modal-feedback-incorrect');

    // Heatmap Elements
    const heatmapCanvas = document.getElementById('heatmap-canvas');
    const btnToggleHeatmap = document.getElementById('btn-toggle-heatmap');
    const btnResetHeatmap = document.getElementById('btn-reset-heatmap');

    // --- INITIALIZATION ---
    updateAlertsQueueHTML();
    updateStatsHeader();
    initSaaSCalculator();
    initLiveVideoEngine();
    initHeatmapEngine();

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
                    <button class="btn-play-clip" data-alert-id="${alert.id}">Rever Clipe</button>
                    <div class="alert-feedback-btns">
                        <button class="btn-feedback correct" title="Confirmar Alerta" data-alert-id="${alert.id}">✓</button>
                        <button class="btn-feedback incorrect" title="Falso Positivo" data-alert-id="${alert.id}">✗</button>
                    </div>
                </div>
            `;
            alertsQueueContainer.appendChild(card);
        });

        // Re-attach event listeners to buttons
        document.querySelectorAll('.btn-play-clip').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.getAttribute('data-alert-id'));
                openAlertModal(id);
            });
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

    // --- REVER CLIPE MODAL PLAYBACK ---

    function openAlertModal(alertId) {
        currentModalAlert = alertsList.find(a => a.id === alertId);
        if (!currentModalAlert) return;

        modalMetaCamera.innerText = currentModalAlert.camera;
        modalMetaTime.innerText = `${currentModalAlert.time}:22`;
        modalMetaTrigger.innerText = currentModalAlert.trigger;
        modalDetectionText.innerText = `${currentModalAlert.title.toUpperCase()} (CONFIANÇA: ${currentModalAlert.confidence}%)`;
        
        videoModal.classList.add('active');
        modalFrame = 0;
        runModalPlayback();
        addLog(`Iniciando reprodução do clipe do Alerta #${alertId} (${currentModalAlert.title}).`);
    }

    function runModalPlayback() {
        const ctx = modalVideoCanvas.getContext('2d');
        const W = modalVideoCanvas.width;
        const H = modalVideoCanvas.height;

        function drawFrame() {
            modalFrame++;
            // Draw background mock supermarket frame
            ctx.fillStyle = '#0a0a0f';
            ctx.fillRect(0, 0, W, H);

            // Draw simple geometric representation of supermarket aisle
            ctx.strokeStyle = '#223';
            ctx.lineWidth = 1;
            for(let i = 0; i < W; i += 40) {
                ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, H); ctx.stroke();
            }

            // Aisle shelves
            ctx.fillStyle = '#181b29';
            ctx.fillRect(80, 50, 120, 260);
            ctx.fillRect(440, 50, 120, 260);

            // Shelf layers and items
            ctx.fillStyle = '#0f172a';
            ctx.fillRect(80, 120, 120, 10);
            ctx.fillRect(80, 190, 120, 10);
            ctx.fillRect(80, 260, 120, 10);
            ctx.fillRect(440, 120, 120, 10);
            ctx.fillRect(440, 190, 120, 10);
            ctx.fillRect(440, 260, 120, 10);

            // Draw items (colorful rectangles)
            ctx.fillStyle = '#f43f5e'; ctx.fillRect(90, 70, 12, 25); ctx.fillRect(105, 70, 10, 25);
            ctx.fillStyle = '#06b6d4'; ctx.fillRect(130, 70, 12, 25); ctx.fillRect(145, 70, 12, 25);
            ctx.fillStyle = '#f59e0b'; ctx.fillRect(460, 70, 14, 25); ctx.fillRect(480, 70, 12, 25);

            // Simulated Person
            const t = (modalFrame % 200) / 200;
            // Person moves from center bottom to shelf, then puts item in pocket
            let px = W/2;
            let py = H - 50;

            if (t < 0.4) {
                // Walking to shelf
                px = W/2 - (W/2 - 240) * (t / 0.4);
                py = H - 50 - (H - 50 - 180) * (t / 0.4);
            } else if (t < 0.6) {
                // Reaching out hand
                px = 240;
                py = 180;
            } else if (t < 0.8) {
                // Moving hand to pocket
                px = 240;
                py = 180;
            } else {
                // Walking away
                px = 240 + (W/2 - 240) * ((t - 0.8) / 0.2);
                py = 180 + (H - 50 - 180) * ((t - 0.8) / 0.2);
            }

            // Draw Bounding Box (YOLO simulation)
            const color = t >= 0.6 ? '#f43f5e' : (t >= 0.4 ? '#f59e0b' : '#00f0ff');
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            const bboxW = 60;
            const bboxH = 120;
            ctx.strokeRect(px - bboxW/2, py - bboxH/2, bboxW, bboxH);

            // Bounding box label
            ctx.fillStyle = color;
            ctx.fillRect(px - bboxW/2, py - bboxH/2 - 18, 90, 18);
            ctx.fillStyle = '#000';
            ctx.font = '10px monospace';
            ctx.fillText(`Pessoa #202 (${Math.round(80 + Math.random()*19)}%)`, px - bboxW/2 + 4, py - bboxH/2 - 5);

            // Pose skeleton lines (complies with behavior triggers, NO face)
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1.5;
            // Head (circle, blank)
            ctx.beginPath();
            ctx.arc(px, py - 40, 8, 0, Math.PI * 2);
            ctx.stroke();
            // Torso
            ctx.beginPath(); ctx.moveTo(px, py - 32); ctx.lineTo(px, py + 10); ctx.stroke();
            // Shoulders
            ctx.beginPath(); ctx.moveTo(px - 15, py - 25); ctx.lineTo(px + 15, py - 25); ctx.stroke();
            // Left Arm
            ctx.beginPath(); ctx.moveTo(px - 15, py - 25); ctx.lineTo(px - 25, py); 
            if (t >= 0.4 && t < 0.6) {
                // reach to shelf
                ctx.lineTo(px - 45, py - 40);
            } else if (t >= 0.6 && t < 0.8) {
                // hand to pocket
                ctx.lineTo(px - 5, py + 5);
            } else {
                ctx.lineTo(px - 20, py + 15);
            }
            ctx.stroke();
            // Right Arm
            ctx.beginPath(); ctx.moveTo(px + 15, py - 25); ctx.lineTo(px + 25, py - 5); ctx.lineTo(px + 20, py + 15); ctx.stroke();
            // Legs
            ctx.beginPath(); ctx.moveTo(px, py + 10); ctx.lineTo(px - 12, py + 50); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(px, py + 10); ctx.lineTo(px + 12, py + 50); ctx.stroke();

            // Draw a floating alert banner inside video on critical trigger
            if (t >= 0.6 && t < 0.85) {
                ctx.fillStyle = 'rgba(255, 0, 85, 0.25)';
                ctx.fillRect(px - 70, py - 80, 140, 22);
                ctx.strokeStyle = '#f43f5e';
                ctx.strokeRect(px - 70, py - 80, 140, 22);
                ctx.fillStyle = '#ff0055';
                ctx.font = 'bold 9px Arial';
                ctx.fillText("ALERTA DE COMPORTAMENTO", px - 64, py - 66);
            }

            // Draw timestamp overlay
            ctx.fillStyle = '#fff';
            ctx.font = '11px Arial';
            ctx.fillText(`CÂMERA BEBIDAS FINAS - REPLAY - CLIPE ALERTA #${currentModalAlert.id}`, 20, 25);

            modalAnimId = requestAnimationFrame(drawFrame);
        }
        
        if (modalAnimId) cancelAnimationFrame(modalAnimId);
        drawFrame();
    }

    btnCloseModal.addEventListener('click', () => {
        videoModal.classList.remove('active');
        if (modalAnimId) cancelAnimationFrame(modalAnimId);
        addLog('Playback do modal finalizado pelo operador.');
    });

    btnModalFeedbackCorrect.addEventListener('click', () => {
        if (currentModalAlert) {
            handleAlertFeedback(currentModalAlert.id, true);
            videoModal.classList.remove('active');
            if (modalAnimId) cancelAnimationFrame(modalAnimId);
        }
    });

    btnModalFeedbackIncorrect.addEventListener('click', () => {
        if (currentModalAlert) {
            handleAlertFeedback(currentModalAlert.id, false);
            videoModal.classList.remove('active');
            if (modalAnimId) cancelAnimationFrame(modalAnimId);
        }
    });

    // Close modal clicking outside
    videoModal.addEventListener('click', (e) => {
        if (e.target === videoModal) {
            videoModal.classList.remove('active');
            if (modalAnimId) cancelAnimationFrame(modalAnimId);
        }
    });


    // --- TAB 1: LIVE CANVAS VIDEO ENGINE ---

    camButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            camButtons.forEach(b => b.classList.remove('active'));
            
            // Allow clicking child elements (indicator dot)
            const targetBtn = e.target.closest('.cam-select-btn');
            targetBtn.classList.add('active');
            
            const camId = parseInt(targetBtn.getAttribute('data-cam'));
            activeCameraId = camId;
            
            const camData = cameraList[camId];
            activeCamTitle.innerText = camData.name;
            
            isSuspiciousActive = false;
            suspiciousPhase = 0;
            detectionNotice.classList.remove('active');
            detectionNotice.innerText = "Nenhuma atividade suspeita no momento";
            
            addLog(`Visualizando fluxo em tempo real: ${camData.name} (${camData.device}).`);
        });
    });

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

    function initLiveVideoEngine() {
        const ctx = videoCanvas.getContext('2d');
        const W = videoCanvas.width;
        const H = videoCanvas.height;

        function renderLive() {
            liveFrame++;
            ctx.fillStyle = '#060a12';
            ctx.fillRect(0, 0, W, H);

            // Draw grid guidelines representing store structure
            ctx.strokeStyle = '#111a2e';
            ctx.lineWidth = 1;
            for(let i = 0; i < W; i += 50) {
                ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, H); ctx.stroke();
            }

            // Draw shelves depending on type
            const camData = cameraList[activeCameraId];
            if (camData.type === 'aisle' || camData.type === 'liquor') {
                // Shelf outlines
                ctx.fillStyle = '#0f172a';
                ctx.fillRect(100, 80, 160, 280);
                ctx.fillRect(540, 80, 160, 280);
                
                // Shelves line
                ctx.fillStyle = '#1e293b';
                ctx.fillRect(100, 150, 160, 12);
                ctx.fillRect(100, 230, 160, 12);
                ctx.fillRect(100, 310, 160, 12);
                ctx.fillRect(540, 150, 160, 12);
                ctx.fillRect(540, 230, 160, 12);
                ctx.fillRect(540, 310, 160, 12);

                // Draw simple items
                ctx.fillStyle = '#3b82f6'; ctx.fillRect(120, 105, 14, 40); ctx.fillRect(140, 105, 14, 40);
                ctx.fillStyle = '#10b981'; ctx.fillRect(170, 105, 12, 40); ctx.fillRect(188, 105, 14, 40);
                ctx.fillStyle = '#eab308'; ctx.fillRect(560, 105, 15, 40); ctx.fillRect(580, 105, 15, 40);
                ctx.fillStyle = '#ef4444'; ctx.fillRect(610, 105, 12, 40); ctx.fillRect(630, 105, 14, 40);
            } else if (camData.type === 'checkout') {
                // Cash register counters
                ctx.fillStyle = '#0f172a';
                ctx.fillRect(200, 200, 400, 120);
                // Conveyor belt
                ctx.fillStyle = '#020617';
                ctx.fillRect(220, 220, 280, 50);
                // Scanner plate
                ctx.fillStyle = '#22d3ee';
                ctx.fillRect(400, 240, 30, 10);
            }

            // Handle Normal / Suspicious Simulation
            if (!isSuspiciousActive) {
                // Draw some casual tracking dots representing empty aisles or normal people walking
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
                    // CONCEALMENT SIMULATION
                    let px = W / 2, py = H - 50, actionState = 'walk';
                    if (timeline < 100) {
                        px = W/2 - (W/2 - 320) * (timeline / 100);
                        py = H - 50 - (H - 50 - 220) * (timeline / 100);
                    } else if (timeline < 220) {
                        px = 320; py = 220; actionState = 'reach';
                    } else if (timeline < 300) {
                        px = 320; py = 220; actionState = 'conceal';
                    } else {
                        px = 320 + (W/2 - 320) * ((timeline - 300) / 80);
                        py = 220 + (H - 50 - 220) * ((timeline - 300) / 80);
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
                    // LINGERING SIMULATION
                    let px = 320, py = 220;
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
                    // RUNNING SIMULATION
                    let px = 50 + (timeline / 380) * (W - 100);
                    let py = H/2 + 50;
                    let trackColor = '#ff0055';
                    detectionNotice.classList.add('active');
                    detectionNotice.innerText = `⚠ ALERTA CRÍTICO: Pessoa correndo no corredor (Velocidade Anormal)`;
                    if (timeline === 100) triggerNewAlert("running");
                    drawTrackObject(ctx, px, py, 110, "Pessoa #205", trackColor, 'run');

                } else if (simType === 'fall') {
                    // CUSTOMER FALL (horizontal skeleton)
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
                    // EMPTY SHELF
                    detectionNotice.classList.add('active');
                    detectionNotice.innerText = `⚠ OPERACIONAL: Gôndola vazia detectada no Corredor 1 (Nível 2)`;
                    if (timeline === 100) triggerNewAlert("shelf");

                    ctx.strokeStyle = '#ff9f00';
                    ctx.lineWidth = 1.5;
                    ctx.setLineDash([4, 4]);
                    ctx.strokeRect(110, 160, 140, 60);
                    ctx.setLineDash([]);
                    
                    ctx.fillStyle = 'rgba(255, 159, 0, 0.2)';
                    ctx.fillRect(110, 160, 140, 60);

                    ctx.fillStyle = '#ff9f00';
                    ctx.fillRect(110, 142, 110, 18);
                    ctx.fillStyle = '#000';
                    ctx.font = 'bold 9px monospace';
                    ctx.fillText("Gôndola Vazia (87%)", 114, 154);
                }
            }

            // Draw current date and camera name
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.font = '12px var(--font-body)';
            ctx.fillText(camData.name.toUpperCase(), 20, 35);
            ctx.font = '10px monospace';
            ctx.fillText(new Date().toLocaleString('pt-BR'), 20, 52);

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
        
        // Rebuild camera grid UI
        rebuildCameraGridHTML();

        // Add camera button to selectors
        const btn = document.createElement('button');
        btn.className = 'cam-select-btn';
        btn.setAttribute('data-cam', newId);
        btn.innerHTML = `<span class="cam-indicator online"></span> ${camName}`;
        document.querySelector('.camera-selectors').appendChild(btn);

        // Add click listener to the newly created button
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.cam-select-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeCameraId = newId;
            activeCamTitle.innerText = camName;
            isSuspiciousActive = false;
            suspiciousPhase = 0;
            detectionNotice.classList.remove('active');
            detectionNotice.innerText = "Nenhuma atividade suspeita no momento";
            addLog(`Visualizando fluxo em tempo real: ${camName} (${camDevice}).`);
        });

        // Reset form
        cameraAddForm.reset();
    });

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
        rebuildCameraGridHTML();

        // Update selector list by removing the camera select button
        const selectorBtn = document.querySelector(`.cam-select-btn[data-cam="${id}"]`);
        if (selectorBtn) selectorBtn.remove();
    }

    // Attach click to pre-existing remove buttons on startup
    rebuildCameraGridHTML();


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
