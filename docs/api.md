# easy
curl -X POST http://localhost:8000/api/v1/chat/ \
-H "Content-Type: application/json" \
-d '{"message":"Хто платник?"}'

#question with context(memory)
curl -X POST http://localhost:8000/api/v1/chat/ \
-H "Content-Type: application/json" \
-d '{
  "session_id":"4310b39a...",
  "message":"А який його рахунок?"
}'

#upload pdf
curl -X POST \
  -F "files=@file1.pdf" \
  -F "files=@file2.pdf" \
  -F "files=@file3.pdf" \
  http://localhost:8000/api/v1/documents/upload

# show colllection
curl http://localhost:6333/collections/erp_documents
#delete collection
curl -X DELETE http://localhost:6333/collections/erp_documents
#import pdf files from dataset
python scripts/upload_dataset.py
#tests
make test-rag                                                 
python3 tests/run_tests.py