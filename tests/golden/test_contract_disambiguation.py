from pathlib import Path

from app.agents.disambiguation import build_disambiguation_answer
from langchain_core.documents import Document
from rules.models import DocumentType

GOLDEN = Path(__file__).parent.parent / "expected" / "contract_disambiguation.txt"


def test_contract_disambiguation_matches_golden():
    chunks = [
        Document(
            page_content="""
Contract Number: C-001
Valid Until: 2027-01-01
""",
            metadata={
                "document_type": DocumentType.CONTRACT,
                "document_name": "Maintenance.pdf",
            },
        ),
        Document(
            page_content="""
Contract Number: C-002
Valid Until: 2028-01-01
""",
            metadata={
                "document_type": DocumentType.CONTRACT,
                "document_name": "Support.pdf",
            },
        ),
    ]

    answer = build_disambiguation_answer(
        "show contract",
        chunks,
    )

    assert answer == GOLDEN.read_text()
