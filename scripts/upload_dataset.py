from pathlib import Path
import requests

API_URL = "http://localhost:8000/api/v1/documents/upload"

DATASET_DIR = Path("tests/datasets")
k = 0

# Рахуємо лише файли (ігноруємо інші папки)
count_files = len([f for f in DATASET_DIR.iterdir() if f.is_file()])
print(f"{count_files} files")
for pdf in DATASET_DIR.glob("*.pdf"):
    k = k + 1
    print(f"[{k}]Uploading {pdf.name}")

    with open(pdf, "rb") as f:
        r = requests.post(API_URL, files={"file": (pdf.name, f, "application/pdf")})

    print(f"{r.status_code} - {r.text}")
