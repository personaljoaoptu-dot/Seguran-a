#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AegisEye AI — End-to-End Stress & Realtime Alert Demonstration Suite
-------------------------------------------------------------------
Este script executa testes de estresse E2E simulando incidentes reais 
processados pela IA local e enviados instantaneamente ao Dashboard Cloud.
"""

import sys
import time
import json
import urllib.request

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

HOST_URL = "https://app.aegiseye.com.br"
TENANT_ID = "a7974ee4-329c-4c06-a57a-0377bcae242e"

DEMO_ALERTS = [
    {
        "tenant_id": TENANT_ID,
        "title": "🚨 SUSPEITA DE OCULTAÇÃO DE MERCADORIA",
        "severity": "critical",
        "camera_name": "Gôndola Bebidas (Adega)",
        "confidence": 94,
        "details": "Indivíduo permaneceu 18s no setor e colocou 2 garrafas em bolsa sem passar pelo caixa.",
        "risk_type": "Ocultação Detectada",
        "video_url": "https://tmpfiles.org/dl/11520173/evidence_sample_1.mp4"
    },
    {
        "tenant_id": TENANT_ID,
        "title": "⚠️ PERMANÊNCIA PROLONGADA EM ZONA RESTRITA",
        "severity": "warning",
        "camera_name": "Corredor 1 (Mercearia)",
        "confidence": 88,
        "details": "Pessoa parada há mais de 45s observando gôndolas de alto valor.",
        "risk_type": "Permanência Suspeita (Loitering)",
        "video_url": "https://tmpfiles.org/dl/11520173/evidence_sample_2.mp4"
    },
    {
        "tenant_id": TENANT_ID,
        "title": "🔵 FLUXO ELEVADO NO AUTOATENDIMENTO",
        "severity": "medium",
        "camera_name": "Autoatendimento",
        "confidence": 91,
        "details": "Acúmulo de clientes sem leitura de itens nos caixas rápidos.",
        "risk_type": "Fila / Atendimento",
        "video_url": ""
    }
]

def run_demo():
    print("=" * 65)
    print("  AEGISEYE AI — SUÍTE DE DEMONSTRAÇÃO E TESTE E2E EM TEMPO REAL")
    print("=" * 65)
    print(f"[TARGET] Servidor Cloud: {HOST_URL}")
    print(f"[TARGET] Tenant ID: {TENANT_ID}\n")

    for idx, alert in enumerate(DEMO_ALERTS, 1):
        print(f"[{idx}/3] Enviando evento de alerta: '{alert['title']}'...")
        payload = json.dumps(alert).encode('utf-8')
        
        req = urllib.request.Request(
            f"{HOST_URL}/api/trigger-alert",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                body = res.read().decode('utf-8')
                resp_data = json.loads(body)
                if resp_data.get('success'):
                    print(f"  ✓ SUCESSO! Alerta gravado no BD e transmitido via SSE (ID: {resp_data['alert']['id']})")
                else:
                    print(f"  ✗ FALHA: {resp_data.get('message')}")
        except Exception as e:
            print(f"  ✗ ERRO de comunicação com o servidor: {e}")
            
        time.sleep(2.5)

    print("\n[E2E TEST] Demonstração finalizada com sucesso!")
    print("Verifique o dashboard em https://app.aegiseye.com.br/index.html para ver os pop-ups e som de alarme.")

if __name__ == '__main__':
    run_demo()
