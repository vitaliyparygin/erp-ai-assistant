# ERP sample

A minimal, runnable example: 4 plain-text ERP documents plus a
`benchmark.yaml` pointing at the `erp` template.

```bash
cd examples/erp_sample
rag-benchmark export --config benchmark.yaml
cat benchmarks/benchmark_queries.json
```

This is intentionally small enough to read `benchmark_queries.json` in
full and see exactly which questions were generated from which extracted
fields — useful as a sanity check when building your own template.
