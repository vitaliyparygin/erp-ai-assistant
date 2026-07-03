# Expected Answers

The following examples illustrate the expected behavior of the AI ERP Assistant.

---

## Vendor Phone

### Question

> Find vendor phone.

### Expected Answer

```
Vendor: Tech Supplies Ltd

Phone: +380671234567

Email: sales@techsupplies.ua
```

Source

- Vendor Profile.pdf

---

## Purchase Order

### Question

> Total sum in Purchase Order PO-2024-001

### Expected Answer

```
Purchase Order

PO Number: PO-2024-001

Supplier: Tech Supply LLC

Customer: Alpha LLC

Amount: 12500 UAH
```

Source

- Purchase Order.pdf

---

## Service Ticket

### Question

> Status ticket TKT-1001

### Expected Answer

```
Status: Closed

Assigned Engineer: John Smith

Customer: Alpha LLC
```

Source

- Service Ticket.pdf

---

## Contractor

### Question

> Who is contractor?

### Expected Answer

The assistant should detect that multiple contracts contain contractor information and ask the user to clarify which contract they mean.

---

## Project Status

### Question

> Show Project Status Report

### Expected Answer

The assistant summarizes the current project status and provides a citation to **PROJECT STATUS REPORT.pdf**.

---

## Customer Complaint

### Question

> Show customer complaint.

### Expected Answer

The assistant retrieves the complaint details and cites **CUSTOMER COMPLAINT.pdf**.

---

## Meeting Minutes

### Question

> Show meeting minutes.

### Expected Answer

The assistant summarizes the meeting discussion and references **MEETING MINUTES.pdf**.