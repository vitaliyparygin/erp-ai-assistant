# API Examples

## Health Check

```bash
curl http://localhost:8000/health
```

---

## Chat Request

## Vendor Phone

```bash
curl -X POST http://localhost:8000/api/v1/chat \
-H "Content-Type: application/json" \
-d '{
  "message":"find vendor phone"
}'
```

---

## Purchase Order

```bash
curl -X POST http://localhost:8000/api/v1/chat \
-H "Content-Type: application/json" \
-d '{
  "message":"total sum in purchase order PO-2024-001"
}'
```

---

## Service Ticket

```bash
curl -X POST http://localhost:8000/api/v1/chat \
-H "Content-Type: application/json" \
-d '{
  "message":"status ticket TKT-1001"
}'
```

---

## Contract Search

```bash
curl -X POST http://localhost:8000/api/v1/chat \
-H "Content-Type: application/json" \
-d '{
  "message":"Who is contractor?"
}'
```

---

## Vendor Agreement

```bash
curl -X POST http://localhost:8000/api/v1/chat \
-H "Content-Type: application/json" \
-d '{
  "message":"Show Vendor Agreement"
}'
```

---

## Upload Documents

```bash
curl -X POST http://localhost:8000/api/v1/documents \
-F "file=@dataset/pdf/sales_manual.pdf"
```

---

## List Documents

```bash
curl http://localhost:8000/api/v1/documents
```

---

## Delete Document

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/{document_id}
```

---

## Conversations

```bash
curl http://localhost:8000/api/v1/conversations
```