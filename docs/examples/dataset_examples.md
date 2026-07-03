# Sample Dataset

The AI ERP Assistant is demonstrated using a collection of ERP-related business documents.

## Available Documents

| Document |
|-----------|
| [Asset Transfer Act.pdf](../tests/datasets/Asset%20Transfer%20Act.pdf) |
| [Bank Statement.pdf](../tests/datasets/Bank%20Statement.pdf) |
| [CRM Opportunity.pdf](../tests/datasets/CRM%20Opportunity.pdf) |
| [Customer Card.pdf](../tests/datasets/Customer%20Card.pdf) |
| [Customer Complaint.pdf](../tests/datasets/CUSTOMER%20COMPLAINT.pdf) |
| [Delivery Note.pdf](../tests/datasets/Delivery_note_2026_0854.pdf) |
| [Delivery Note DN-2026-88412.pdf](../tests/datasets/DELIVERY_NOTE_DN-2026-88412.pdf) |
| [Employment Contract.pdf](../tests/datasets/EMPLOYMENT%20CONTRACT.pdf) |
| [ERP Master Contract.pdf](../tests/datasets/erp_master_contract.pdf) |
| [Insurance Policy.pdf](../tests/datasets/INSURANCE%20POLICY.pdf) |
| [Internet Invoice.pdf](../tests/datasets/internet_invoice.pdf) |
| [Invoice.pdf](../tests/datasets/Invoice.pdf) |
| [Leave Order.pdf](../tests/datasets/Leave%20Order.pdf) |
| [Maintenance Contract.pdf](../tests/datasets/Maintenance%20Contract.pdf) |
| [Meeting Minutes.pdf](../tests/datasets/MEETING%20MINUTES.pdf) |
| [NDA Agreement.pdf](../tests/datasets/NDA%20Agreement.pdf) |
| [Procurement Request.pdf](../tests/datasets/Procurement%20Request.pdf) |
| [Project Charter.pdf](../tests/datasets/Project%20Charter.pdf) |
| [Project Status Report.pdf](../tests/datasets/PROJECT%20STATUS%20REPORT.pdf) |
| [Purchase Order.pdf](../tests/datasets/Purchase%20Order.pdf) |
| [Purchase Order P00019.pdf](../tests/datasets/Purchase%20Order%20-%20P00019.pdf) |
| [Rental Agreement.pdf](../tests/datasets/RENTAL%20AGREEMENT.pdf) |
| [Salary Statement.pdf](../tests/datasets/Salary%20Statement.pdf) |
| [Service Contract.pdf](../tests/datasets/service_contract.pdf) |
| [Service Ticket.pdf](../tests/datasets/Service%20Ticket.pdf) |
| [Timesheet.pdf](../tests/datasets/Timesheet.pdf) |
| [Vendor Agreement.pdf](../tests/datasets/Vendor%20Agreement.pdf) |
| [Vendor Profile.pdf](../tests/datasets/Vendor%20Profile.pdf) |

## Dataset Structure

```text
dataset/
│
├── pdf/
├── markdown/
├── json/
├── txt
├── wav/
└── metadata/

```

---

## Scripts

```bash
make upload_dataset #create dataset
make reindex        #recreate dataset
make clear_dataset  #delete dataset
make check_set      #run script check dataset
```


---

## Supported Formats

- PDF
