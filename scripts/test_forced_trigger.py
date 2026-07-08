#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AegisEye AI - Forced Alert Trigger Test Script
-----------------------------------------------
Este script simula o disparo de um alerta completo e válido contendo todos
os campos obrigatórios: camera_id, timestamp e risk_type/evento.
Pode enviar via POST para o webhook n8n ou diretamente para a base de dados Postgres.
"""

import os
import sys
import json
import datetime
import urllib.request

# Default valid configurations for João Pedro (Tenant ID / Camera)
DEFAULT_TENANT_ID = "a7974ee4-329c-4c06-a57a-0377bcae242e"
DEFAULT_CAMERA_ID = "b83624ce-3062-40c6-a6fa-cc154ddf7bbf" # Canal 3 - DVR (INTELBRAS)
DEFAULT_CAMERA_NAME = "Canal 3 - DVR (INTELBRAS)"

N8N_WEBHOOK_URL = "http://144.91.121.55:5678/webhook/e5f6a7b8-cdbe-4712-a1f9-d892a01f30f6/webhook/aegiseye-alerts"

DB_HOST = "144.91.121.55"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASS = "KtnYcxnVOGjD4thzS6tlBcW9"
DB_NAME = "aegisyear"

def generate_payload():
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "tenant_id": DEFAULT_TENANT_ID,
        "user_id": None,
        "camera_id": DEFAULT_CAMERA_ID,
        "camera_name": DEFAULT_CAMERA_NAME,
        "severity": "critical",
        "title": "Alerta Forçado - Ocultamento IA (Simulado)",
        "details": "Este é um alerta simulado de alta prioridade gerado para testes do fluxo de dados.",
        "confidence": 98.4,
        "confidence_score": 98.4,
        "trigger_type": "CONCEALMENT_ROI",
        "risk_type": "CONCEALMENT_ROI",
        "track_id": 404,
        "url_video": "https://www.w3schools.com/html/mov_bbb.mp4",
        "evento": "CONCEALMENT_ROI",
        "timestamp": now_iso
    }
    return payload

def send_via_webhook(payload):
    print(f"[TESTE-WEBHOOK] Enviando payload para o n8n...")
    print(json.dumps(payload, indent=2))
    
    try:
        req = urllib.request.Request(
            N8N_WEBHOOK_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = response.read().decode('utf-8')
            print(f"[TESTE-WEBHOOK SUCCESS] Resposta: {res_data}")
            return True
    except Exception as e:
        print(f"[TESTE-WEBHOOK ERROR] Falha no envio para o webhook: {e}")
        return False

def insert_via_db(payload):
    print(f"[TESTE-DB] Inserindo registro diretamente no banco de dados...")
    try:
        import pg8000
        import uuid
        
        conn = pg8000.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            timeout=5
        )
        cursor = conn.cursor()
        
        alert_uuid = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO public.alertas (
                id, tenant_id, user_id, camera_id, camera_name, severity, title, details, confidence_score, risk_type, track_id, video_url, timestamp, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
            RETURNING id
        """, (
            alert_uuid, payload["tenant_id"], payload["user_id"], payload["camera_id"], payload["camera_name"],
            payload["severity"], payload["title"], payload["details"], payload["confidence_score"], payload["risk_type"],
            payload["track_id"], payload["url_video"], payload["timestamp"]
        ))
        
        inserted_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[TESTE-DB SUCCESS] Alerta inserido com ID: {inserted_id}")
        return True
    except Exception as e:
        print(f"[TESTE-DB ERROR] Falha na conexão/inserção do banco: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print(" AegisEye - Forced Trigger Testing Tool")
    print("=" * 60)
    
    payload = generate_payload()
    
    # 1. Try n8n webhook first
    success = send_via_webhook(payload)
    
    # 2. Fall back to direct database insertion if webhook failed
    if not success:
        print("\nTentando fallback: Inserindo diretamente no Banco de Dados da VPS...")
        insert_via_db(payload)
    else:
        print("\n[SUCESSO] Alerta simulado despachado via webhook.")
        
    print("\nVerifique a Fila de Alertas Operacionais no painel web para confirmar o surgimento do alerta em tempo real.")
