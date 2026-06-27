#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AegisEye AI - Core Computer Vision Pipeline
-------------------------------------------
Este script simula o pipeline real de detecção, rastreamento e análise comportamental
rodando no Edge Node do supermercado, sem expor dados biométricos (LGPD Compliant).

Ele simula o processamento de frames em tempo real, aplicação de estimativa de pose,
regras de permanência e envio de alertas operacionais para a API central.
"""

import time
import json
import random
import sys
import math

class SimulatedVideoSource:
    """Simula a captura de frames de uma câmera IP via RTSP (Intelbras / Hikvision)"""
    def __init__(self, rtsp_url, name):
        self.rtsp_url = rtsp_url
        self.name = name
        self.frame_id = 0
        print(f"[INPUT] Conectado ao stream RTSP: {rtsp_url} ({name})")

    def read_frame(self):
        """Retorna dados simulados que representam a imagem atual e as coordenadas obtidas"""
        self.frame_id += 1
        time.sleep(0.033) # Simula ~30 FPS
        return {
            "frame_id": self.frame_id,
            "timestamp": time.time(),
            "width": 1920,
            "height": 1080
        }

class AegisEyeProcessor:
    """Processador de IA rodando algoritmos de detecção, pose e regras de negócio"""
    def __init__(self, camera_name):
        self.camera_name = camera_name
        self.tracks = {} # ID -> {"positions": [(x, y)], "time_entered": t}
        self.lingering_threshold = 15.0 # segundos para alerta de permanência
        print(f"[ENGINE] Inicializado modelos YOLOv8-Detection e YOLOv8-Pose para: {camera_name}")

    def process_frame(self, frame_data):
        """Aplica os detectores e verifica regras de comportamento no frame"""
        alerts = []
        frame_id = frame_data["frame_id"]
        
        # 1. Simulação do YOLO Object Detection (Saída: Bounding Boxes)
        # Formato: [x, y, w, h, class, confidence]
        detections = []
        
        # Simula uma pessoa entrando após frame 30
        if frame_id > 30:
            # Pessoa #194 caminhando em direção à adega
            progress = min(1.0, (frame_id - 30) / 120.0)
            px = int(960 - (960 - 640) * progress)
            py = int(800 - (800 - 540) * progress)
            detections.append({
                "track_id": 194,
                "bbox": [px - 100, py - 300, 200, 600],
                "class": "person",
                "conf": 0.94
            })
            
            # 2. Simulação do YOLO-Pose (Keypoints para detectar queda ou ocultamento)
            # Se a pessoa estiver parada na adega (progress == 1.0)
            if progress >= 1.0:
                # Simula cálculo de pose: braço cruza o peito rapidamente (ocultamento)
                if frame_id == 160:
                    alerts.append({
                        "severity": "critical",
                        "title": "Remoção e ocultação rápida",
                        "details": "Objeto removido da gôndola e inserido sob a jaqueta.",
                        "camera": self.camera_name,
                        "confidence": 89,
                        "trigger": "Pose estimation: Keypoint de mão direita interceptou bounding box de produto caro -> ocultado na jaqueta em 0.4s.",
                        "code": "CONCEALMENT_FAST"
                    })

        # Simula outra pessoa que pode cair no chão (Segurança Civil)
        if frame_id > 100 and frame_id < 250:
            # Pessoa #211
            px = 1200
            py = 700
            if frame_id < 150:
                detections.append({
                    "track_id": 211,
                    "bbox": [px - 100, py - 300, 200, 600],
                    "class": "person",
                    "pose": "standing",
                    "conf": 0.91
                })
            else:
                # Cai no chão
                detections.append({
                    "track_id": 211,
                    "bbox": [px - 300, py + 100, 600, 200], # Bounding box horizontal
                    "class": "person",
                    "pose": "fallen",
                    "conf": 0.96
                })
                if frame_id == 155:
                    alerts.append({
                        "severity": "critical",
                        "title": "Queda de cliente detectada",
                        "details": "Emergência: Sensor de pose detectou cliente caído no chão.",
                        "camera": self.camera_name,
                        "confidence": 94,
                        "trigger": "Pose skeleton: Keypoint do pescoço e quadris alinhados na horizontal a < 20cm do solo.",
                        "code": "CUSTOMER_FALL"
                    })

        return detections, alerts

def send_alert_to_dashboard(alert):
    """Envia o alerta gerado para a API de monitoramento central (Simulado)"""
    print(f"\n[⚠️ ALERTA DISPARADO]")
    print(f"  Tipo: {alert['severity'].upper()} | Título: {alert['title']}")
    print(f"  Detalhes: {alert['details']}")
    print(f"  Câmera: {alert['camera']} | Confiança: {alert['confidence']}%")
    print(f"  Código Técnico: {alert['code']}")
    print(f"  Trigger: {alert['trigger']}")
    print("-" * 50)

def main():
    print("=" * 60)
    print(" AegisEye AI - Pipeline de Processamento de Vídeo em Python")
    print("=" * 60)
    
    # Inicializa fonte de vídeo e o processador
    video = SimulatedVideoSource("rtsp://192.168.1.100/ch3", "Bebidas Finas")
    processor = AegisEyeProcessor("Bebidas Finas")
    
    print("\n[INFO] Iniciando loop de processamento de vídeo. Pressione Ctrl+C para encerrar.\n")
    try:
        while True:
            # 1. Grab frame
            frame = video.read_frame()
            
            # 2. Process frame
            detections, alerts = processor.process_frame(frame)
            
            # 3. Print processing stats (periodic)
            if frame["frame_id"] % 30 == 0:
                print(f"[PROCESS] Frame {frame['frame_id']} processado. Objetos rastreados: {len(detections)}")
                for det in detections:
                    print(f"   -> Track ID #{det['track_id']} ({det['class']}) Confiança: {det['conf']}")
            
            # 4. Handle any detected alerts
            for alert in alerts:
                send_alert_to_dashboard(alert)
                
            # Interrompe a simulação após 220 frames para demonstração limpa
            if frame["frame_id"] >= 220:
                print("\n[INFO] Simulação de pipeline concluída com sucesso (220 frames).")
                break
                
    except KeyboardInterrupt:
        print("\n[INFO] Interrompido pelo usuário.")
        sys.exit(0)

if __name__ == "__main__":
    main()
