import os
import json

n8n_dir = "n8n"
for filename in os.listdir(n8n_dir):
    if filename.endswith(".json"):
        filepath = os.path.join(n8n_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"{filename}: active = {data.get('active')}")
