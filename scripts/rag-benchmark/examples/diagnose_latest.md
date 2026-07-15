# rag-benchmark Diagnostics Report

Generated: 2026-07-14 12:00 UTC

---

# Pipeline

| Stage | Result |
|--------|--------|
| Files scanned | 31 |
| Documents classified | 31 |
| Metadata extracted | 31 |
| Questions generated | 176 |

---

# Classification

| Document Type | Count |
|--------------|------:|
| Invoice | 4 |
| Purchase Order | 3 |
| Vendor Profile | 2 |
| Service Ticket | 2 |
| CRM Opportunity | 2 |
| Bank Statement | 1 |
| Contract | 5 |
| Employee | 4 |
| Unknown | 8 |

---

# Metadata Coverage

| Field | Coverage |
|------|---------:|
| invoice_number | 100% |
| amount | 100% |
| currency | 100% |
| vendor | 92% |
| due_date | 95% |
| po_number | 100% |

---

# Question Generation

| Metric | Value |
|--------|------:|
| Total questions | 176 |
| Average per document | 5.7 |
| Maximum | 6 |
| Minimum | 0 |

---

# Readiness

| Category | Score |
|----------|------:|
| Classification | 96% |
| Metadata | 94% |
| Question Generation | 91% |

Overall benchmark readiness:

**94% (Excellent)**

---

# Recommendations

## Unknown document types

- Asset Transfer Act.pdf
- Customer Card.pdf

Consider adding classification rules.

---

## Missing extraction fields

Purchase Order

- delivery_date

Vendor Profile

- address

---

## Suggested regexes

delivery_date

```
Delivery Date[:\s]+(.+)
```

address

```
Address[:\s]+(.+)
```

---

No unused regexes were detected.