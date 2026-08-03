from rules.models import DocumentType
from langchain_core.documents import Document
from app.agents.disambiguation import build_disambiguation_answer

chunk = Document(
    page_content="Contract Number: C-001\nValid Until: 2026-12-31",
    metadata={
        "document_name": "Contract.pdf",
        "document_type": DocumentType.CONTRACT,
    },
)


def test_returns_none_when_single_contract():
    chunks = [
        Document(
            page_content="Contract Number: C-001\nValid Until: 2027-01-01",
            metadata={
                "document_name": "contract1.pdf",
                "document_type": DocumentType.CONTRACT,
            },
        )
    ]

    assert build_disambiguation_answer("", chunks) is None


def test_returns_none_when_not_contract():
    chunks = [
        Document(
            page_content="Contract Number: C-001\nValid Until: 2027-01-01",
            metadata={
                "document_type": DocumentType.INVOICE,
                "document_name": "invoice.pdf",
            },
        )
    ]

    assert build_disambiguation_answer("", chunks) is None


def test_builds_contract_list():
    chunks = [
        Document(
            page_content="Contract Number: C-001\nValid Until: 2027-01-01",
            metadata={
                "document_name": "contract1.pdf",
                "document_type": DocumentType.CONTRACT,
            },
        ),
        Document(
            page_content="Contract Number: C-002\nValid Until: 2028-01-01",
            metadata={
                "document_name": "contract2.pdf",
                "document_type": DocumentType.CONTRACT,
            },
        ),
    ]

    answer = build_disambiguation_answer("Show me the contract", chunks)

    assert answer is not None
    assert "contract1.pdf" in answer
    assert "contract2.pdf" in answer
    assert "C-001" in answer
    assert "C-002" in answer
