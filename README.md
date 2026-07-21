# AegisEye AI — Loss Prevention & Computer Vision Platform

[![Status](https://img.shields.io/badge/Status-Production%20Ready-emerald.svg)](https://app.aegiseye.com.br)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://www.docker.com/)
[![YOLOv8](https://img.shields.io/badge/AI%20Model-YOLOv8-FF6F61.svg)](https://ultralytics.com)
[![License](https://img.shields.io/badge/License-Proprietary-slate.svg)](#)

**AegisEye AI** é uma plataforma de ponta para prevenção de perdas no varejo e análise preditiva comportamental em tempo real. O sistema utiliza técnicas avançadas de **Visão Computacional**, **Deep Learning (YOLOv8)**, **Stream RTSP de baixa latência** e integração com **n8n e PostgreSQL** para detectar incidentes, monitorar mapas de calor (heatmaps de risco) e notificar equipes de segurança de forma imediata.

---

## 🏛️ Arquitetura do Sistema

O ecossistema **AegisEye** é dividido em três camadas principais interconectadas:

```
┌────────────────────────────────┐       ┌─────────────────────────────────┐
│     Edge Node (Local AI)       │       │    Cloud Web Dashboard & API    │
│  - Pipeline Visão Computacional│ RTSP  │  - Python Fast HTTP Server      │
│  - Leitura RTSP (TCP)          ├──────►│  - Analytics & Risk Heatmaps    │
│  - Detecção YOLOv8 em Tempo Real│ WebRTC│  - Gestão Multitenant & Câmeras │
└───────────────┬────────────────┘       └────────────────┬────────────────┘
                │                                         │
                │             ┌───────────┐               │
                └────────────►│ PostgreSQL├───────────────┘
                              │  & n8n    │
                              │Workflows  │
                              └───────────┘
```

1. **Edge AI Node (`scripts/aegiseye_vision_pipeline.py` & `local_camera_streamer.py`)**:
   - Processamento de vídeo direto nas câmeras do estabelecimento (RTSP via TCP).
   - Inferência computacional com modelo YOLOv8 otimizado para detecção de comportamentos suspeitos e contagem.
   - Streaming dinâmico multipart HTTP/MJPEG em portas dedicada (8082) com fallback automático.

2. **Web Dashboard (`frontend/` & `server.py`)**:
   - Interface SPA (Single Page Application) em Vanilla HTML5/CSS3/JS modular com temas escuros futuristas.
   - Monitoramento em live stream, mapas de calor interativos, gráficos de tendência por faixa horária e métricas de ROI SaaS.
   - Autenticação e gestão por perfil Tenant/Usuário.

3. **Orquestração & Persistência (`n8n/` & `postgresql/`)**:
   - Workflows automatizados de e-mail de ativação, alertas push, validação de empresas/usuários.
   - Banco de dados PostgreSQL com esquemas relacionais otimizados para métricas de eventos e auditoria LGPD.

---

## 📂 Estrutura do Repositório

```
aegiseye-dashboard/
├── frontend/                        # Interface Web do Dashboard Cloud
│   ├── index.html                   # Painel Principal (Analytics, Heatmaps, Cameras & Live Stream)
│   ├── login.html                   # Tela de Autenticação
│   ├── activate.html                # Tela de Ativação de Conta
│   ├── app.js                       # Lógica de Controle SPA, WebSocket e Gráficos
│   └── style.css                    # Design System & Estilos Globais (Glassmorphism UI)
├── scripts/                         # Automações de Deploy e Pipelines
│   ├── aegiseye_vision_pipeline.py  # Engine de Visão Computacional (YOLOv8 + OpenCV)
│   ├── deploy_remote.py             # Script de Deploy Automatizado (SSH / SFTP / Docker Remote)
│   ├── create_test_user.py          # Utilitário de Bootstrap de Usuários
│   └── test_forced_trigger.py       # Teste de Estresse de Alertas
├── n8n/                             # Fluxos de Automação n8n (JSON Workflows)
│   ├── aegiseye_auth_workflow.json
│   ├── n8n_registration_workflow.json
│   ├── n8n_activation_workflow.json
│   ├── n8n_camera_config_workflow.json
│   └── n8n_alerts_workflow.json
├── postgresql/                      # DDLs e Esquemas SQL do Banco de Dados
│   ├── aegiseye_alerts_schema.sql   # Tabela de Alertas e Incidentes
│   ├── registration_schema.sql      # Tabela de Usuários e Tenants
│   └── activation_schema.sql        # Tabela de Tokens de Ativação
├── AegisEyeDesktopWeb.py            # Launcher Desktop Nativo (PyWebView GUI Wrapper)
├── local_camera_streamer.py         # Servidor de Stream Local (Fallback)
├── desktop_ui.html                  # Interface Nativa do Aplicativo Desktop
├── server.py                        # Backend HTTP Python / API Gateway Dashboard
├── Dockerfile                       # Containerização da Aplicação
├── docker-compose.yml               # Orquestração Multisserviço Cloud
└── cameras.json                     # Registro de Câmeras do Estabelecimento
```

---

## 🚀 Como Executar o Projeto

### 1. Requisitos Prévios
- **Python 3.11+**
- **Docker & Docker Compose** (para ambiente de produção ou servidor)
- Câmeras IP compatíveis com protocolo RTSP

### 2. Rodar o Backend Localmente
```bash
# Instalar dependências
pip install opencv-python ultralytics requests psycopg2-binary pywebview

# Iniciar o servidor backend do dashboard (Porta 8000)
python server.py
```
Acesse a aplicação em `http://localhost:8000`.

### 3. Rodar a Aplicação Desktop Nativa
```bash
python AegisEyeDesktopWeb.py
```

---

## 🛠️ Deploy Automatizado na Nuvem

O projeto conta com um script de deploy remoto de um clique (`scripts/deploy_remote.py`):

```bash
python scripts/deploy_remote.py
```

O script realiza automaticamente:
1. Conexão SSH / SFTP segura com o servidor cloud (`app.aegiseye.com.br`).
2. Sincronização dos arquivos do frontend, backend e schemas.
3. Build e deploy limpo dos contêineres Docker (`docker compose up -d --build`).
4. Importação e ativação dos workflows no contêiner `n8n`.

---

## 🔒 Conformidade & Segurança
- **LGPD Compliant**: O processamento de imagem para detecção de comportamento não realiza biometria ou armazenamento facial prolongado.
- **Isolamento Multitenant**: Dados segregados por `tenant_id` e chaves de sessão criptografadas.

---

© 2026 AegisEye AI. Todos os direitos reservados.
