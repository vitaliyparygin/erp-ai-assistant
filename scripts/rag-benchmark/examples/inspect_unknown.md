# rag-benchmark inspect

Command

```bash
rag-benchmark inspect \
    --dataset tests/datasets \
    --file "Asset Transfer Act.pdf"
```

---

# Document

```
Asset Transfer Act.pdf
```

## Classification

| Property | Value |
|----------|-------|
| Document type | Unknown |
| Confidence | 0.00 |
| Status | ❌ Not classified |

---

# Classification candidates

| Candidate | Confidence |
|-----------|-----------:|
| Contract | 0.28 |
| Purchase Order | 0.17 |
| Invoice | 0.12 |

No candidate exceeded the classification threshold.

---

# Extracted metadata

No metadata was extracted.

---

# Expected fields

Unknown document type.

No extraction rules are currently available.

---

# Detected keywords

```
asset
transfer
equipment
owner
effective date
department
serial number
location
```

---

# Suggested classification rule

The document appears similar to an **Asset Transfer** document.

Suggested rule:

```python
ClassificationRule(
    document_type="Asset Transfer",
    keywords=[
        "asset transfer",
        "serial number",
        "transfer date",
        "department",
        "asset id",
    ],
)
```

---

# Suggested metadata fields

| Field | Suggested Labels |
|-------|------------------|
| asset_id | Asset ID, Asset Number |
| serial_number | Serial Number |
| transfer_date | Transfer Date |
| from_department | From Department |
| to_department | To Department |
| owner | Owner |

---

# Suggested regexes

### asset_id

```regex
Asset\s*(ID|Number)\s*[:#]?\s*(.+)
```

### serial_number

```regex
Serial\s*Number\s*[:#]?\s*(.+)
```

### transfer_date

```regex
Transfer\s*Date\s*[:#]?\s*(.+)
```

### owner

```regex
Owner\s*[:#]?\s*(.+)
```

---

# Question generation

No questions were generated.

Reason:

- document type is Unknown
- no question templates are available

---

# Recommendations

## Add a classification rule

Create a new `ClassificationRule` for **Asset Transfer**.

## Add extraction rules

Recommended fields:

- asset_id
- serial_number
- transfer_date
- from_department
- to_department
- owner

## Add question templates

Example questions:

- What is the asset ID?
- What is the serial number?
- Who owns the asset?
- Which department transferred the asset?
- What is the transfer date?

---

# Summary

| Metric | Value |
|--------|------:|
| Classification | ❌ Unknown |
| Metadata coverage | 0% |
| Generated questions | 0 |
| Suggested rules | 1 |
| Suggested regexes | 4 |

Overall readiness:

**Needs template support**