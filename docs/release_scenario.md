## Release Scenario

0. Clean state
````
git status
git pull
````

1. Static checks
````
ruff check app tests
mypy app
pytest -q -W error
````


2. Build clean Docker images
````
docker compose build --no-cache
````


3. Start stack
````
docker compose up -d

docker compose ps
````
   check:

* backend — Up
* worker — Up
* postgres — healthy
* redis — healthy
* qdrant — Up
* ollama — Up
* frontend — Up


4. Health
````
curl http://localhost:8000/health

curl http://localhost:8000/health/ready
````
Gate: readiness = healthy.


5. Qdrant
````
curl http://localhost:6333/collections
````


{
  "result": {
    "collections": [...]
  },
  "status": "ok"
}


````
curl http://localhost:6333/collections/erp_documents
````


6. Ollama
````
curl http://localhost:11434/api/tags
````


7. Dataset

````

python3 scripts/upload_dataset.py

docker compose logs worker --tail=100
````

````
curl http://localhost:6333/collections/erp_documents
````


8. Document API

````
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@tests/datasets/Invoice.pdf"
````


9. Real RAG query


````
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"яка сума в інвойсі INT-2024-555?"}'

````
