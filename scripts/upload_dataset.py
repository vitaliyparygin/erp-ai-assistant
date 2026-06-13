from pathlib import Path
import requests

API_URL = "http://localhost:8000/api/v1/documents/upload"

DATASET_DIR = Path("tests/datasets")

for pdf in DATASET_DIR.glob("*.pdf"):
    print(f"Uploading {pdf.name}")

    with open(pdf, "rb") as f:
        r = requests.post(
            API_URL,
            files={"file": (pdf.name, f, "application/pdf")}
        )

    print(r.status_code)
    print(r.text)