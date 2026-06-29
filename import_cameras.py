import json
import argparse
import sys

try:
    import requests
except ImportError:
    print("[WARN] Biblioteca 'requests' não encontrada. Instalando automaticamente...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

def main():
    parser = argparse.ArgumentParser(description="AegisEye CLI - Importador de Câmeras em Lote")
    parser.add_argument("--file", default="cameras.json", help="Caminho do arquivo JSON de entrada")
    parser.add_argument("--tenant", default="17ae7c70-afd3-4e26-b2a6-63bfa07ef516", help="Tenant ID associado")
    parser.add_argument("--url", default="http://144.91.121.55:8000/api/configurar", help="URL do endpoint de configuração")
    args = parser.parse_args()

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            cameras = json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{args.file}' não foi encontrado.")
        sys.exit(1)
    except json.JSONDecodeError as je:
        print(f"Erro: Falha ao decodificar JSON do arquivo '{args.file}': {je}")
        sys.exit(1)

    if not isinstance(cameras, list):
        print("Erro: O arquivo de configuração deve ser um array JSON de objetos.")
        sys.exit(1)

    print(f"Iniciando importação de {len(cameras)} câmera(s) no tenant '{args.tenant}'...")

    for cam in cameras:
        nome = cam.get("nome", "").strip()
        url_rtsp = cam.get("url_rtsp", "").strip()
        localizacao = cam.get("localizacao", "").strip()

        if not nome or not url_rtsp:
            print(f"[ERRO] Câmera ignorada: nome e url_rtsp são obrigatórios.")
            continue

        # Map frontend schema to database schema
        payload = {
            "action": "add_camera",
            "tenant_id": args.tenant,
            "name": nome,
            "device": "Dispositivo Importado via CLI",
            "rtsp": url_rtsp,
            "profile": localizacao or "Geral",
            "type": "checkout" if "caixa" in nome.lower() or "checkout" in nome.lower() else "aisle",
            "status": "online"
        }

        try:
            res = requests.post(args.url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
            if res.status_code == 200:
                print(f"Câmera {nome} configurada com sucesso")
            else:
                print(f"Erro ao configurar câmera {nome}: HTTP {res.status_code} - {res.text}")
        except Exception as e:
            print(f"Erro de conexão ao configurar câmera {nome}: {e}")

if __name__ == "__main__":
    main()
