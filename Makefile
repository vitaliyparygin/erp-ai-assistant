test-rag:
	python3 tests/run_tests.py
upload_dataset:
	python3 scripts/upload_dataset.py
clear_dataset:
	curl -X DELETE http://localhost:6333/collections/erp_documents
reindex:
	 curl -X DELETE http://localhost:6333/collections/erp_documents && python3 scripts/upload_dataset.py
check_set:
	docker compose exec backend python -m scripts.check_ingestion
