# rag-benchmark inspect

Command

```bash
rag-benchmark inspect \
    --dataset tests/datasets \
    --file "Invoice.pdf"
```

---

# Document

```
Invoice.pdf
```

Document type

```
Invoice
```

Confidence

```
0.96
```

---

# Extracted metadata

| Field | Value |
|------|------|
| invoice_number | INV-2026-1023 |
| customer | ACME Corporation |
| amount | 12450.00 |
| currency | USD |
| issue_date | 2026-04-15 |
| due_date | 2026-05-15 |

---

# Expected fields

- invoice_number
- customer
- amount
- currency
- issue_date
- due_date

---

# Missing fields

None

---

# Generated questions

### Question 1

```
What is the invoice number of Invoice.pdf?
```

Expected answer

```
INV-2026-1023
```

---

### Question 2

```
Who is the customer?
```

Expected answer

```
ACME Corporation
```

---

### Question 3

```
What is the invoice amount?
```

Expected answer

```
12450.00 USD
```

---

### Question 4

```
When is the payment due?
```

Expected answer

```
2026-05-15
```

---

# Regex diagnostics

| Field | Status |
|------|------|
| invoice_number | ✓ matched |
| customer | ✓ matched |
| amount | ✓ matched |
| currency | ✓ matched |
| issue_date | ✓ matched |
| due_date | ✓ matched |

---

# Coverage

| Metric | Value |
|--------|------:|
| Expected fields | 6 |
| Extracted fields | 6 |
| Coverage | 100% |

---

# Suggestions

No improvements required.

The document is fully supported by the current template.