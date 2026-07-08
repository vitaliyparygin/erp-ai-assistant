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
benchmark:
	python3 scripts/benchmark.py
benchmark-init:
	rag-benchmark init --output my-benchmark --template erp
benchmark-scan:
	rag-benchmark scan     --config my-benchmark/benchmark.yaml
benchmark-generate:
	rag-benchmark generate --config my-benchmark/benchmark.yaml
benchmark-report:
	rag-benchmark report   --config my-benchmark/benchmark.yaml
benchmark-validate:
	rag-benchmark validate --config my-benchmark/benchmark.yaml
benchmark-export:
	rag-benchmark export   --config my-benchmark/benchmark.yaml
