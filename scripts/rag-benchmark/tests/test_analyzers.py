"""Tests for rag_benchmark.extractor."""

from __future__ import annotations

from rag_benchmark.analyzers.document_summary import DocumentSummaryAnalyzer
from rag_benchmark.analyzers.field_coverage import FieldCoverageAnalyzer
from rag_benchmark.diagnostics.models import QuestionCoverage
from rag_benchmark.analyzers.question_coverage import QuestionCoverageAnalyzer
from rag_benchmark.analyzers.regex_analyzer import RegexAnalyzer
from rag_benchmark.models import BenchmarkQuery, Difficulty
from types import SimpleNamespace
from rag_benchmark.diagnostics.models import FieldCoverage

from rag_benchmark.analyzers.regex_analyzer import RegexStat

def test_field_coverage():
    classified = SimpleNamespace(
        metadata=SimpleNamespace(
            fields={
                "vendor": "Tech Ltd",
                "amount": "100",
            }
        )
    )

    result = FieldCoverageAnalyzer.analyze(
        classified,
        [
            "vendor",
            "amount",
            "date",
        ],
    )

    assert result.expected == [
        "vendor",
        "amount",
        "date",
    ]

    assert result.extracted == [
        "vendor",
        "amount",
    ]

    assert result.missing == [
        "date",
    ]

    assert result.coverage == 2 / 3



class Rule:
    def __init__(self, field_name, patterns):
        self.field_name = field_name
        self.patterns = patterns

def test_regex_analyzer():
    document = SimpleNamespace(
        classification=SimpleNamespace(
            document_type="Vendor Profile",
        ),
        document=SimpleNamespace(
            text="""
Vendor Name: Tech Supplies Ltd
Phone: +380671234567
Email: sales@test.com
"""
        ),
    )

    template = SimpleNamespace(
        extraction_rules={
            "Vendor Profile": (
                Rule(
                    "vendor",
                    (
                        r"Vendor\s*Name:\s*(.+)",
                    ),
                ),
                Rule(
                    "phone",
                    (
                        r"Phone:\s*([+\d]+)",
                    ),
                ),
                Rule(
                    "email",
                    (
                        r"Email:\s*(.+)",
                    ),
                ),
            )
        }
    )

    result = RegexAnalyzer.analyze(
        document,
        template,
    )
    assert len(result) == 3

    assert result[0].field == "vendor"
    assert result[0].matches == 1

    assert result[1].field == "phone"
    assert result[1].matches == 1

    assert result[2].field == "email"
    assert result[2].matches == 1

def test_question_coverage():

    questions = [
        BenchmarkQuery(
            id=1,
            query="Vendor?",
            expected_document="Vendor.pdf",
            expected_fields=["vendor"],
            document_type="Vendor Profile",
            difficulty=Difficulty.EASY,
            tags=["erp"],
        ),
        BenchmarkQuery(
            id=2,
            query="Amount?",
            expected_document="Vendor.pdf",
            expected_fields=["amount"],
            document_type="Vendor Profile",
            difficulty=Difficulty.EASY,
            tags=["erp"],
        ),
    ]

    result = QuestionCoverageAnalyzer.analyze(
        expected_fields=[
            "vendor",
            "amount",
            "date",
        ],
        questions=questions,
    )

    assert result.generated == 2
    assert result.skipped == 1
    assert result.generated_fields == [
        "vendor",
        "amount",
    ]

    assert result.missing_fields == [
        "date",
    ]



def test_document_summary():

    classified = SimpleNamespace(
        classification=SimpleNamespace(
            document_type="Invoice",
        ),
        document=SimpleNamespace(
            filename="Invoice.pdf",
        ),
    )

    field_result = FieldCoverage(
        expected=[
            "invoice_number",
            "amount",
            "customer",
        ],
        extracted=[
            "invoice_number",
            "amount",
        ],
        missing=[
            "customer",
        ],
        coverage=2 / 3,
    )

    regex_result = [
        RegexStat(
            document_type="Invoice",
            field="invoice_number",
            pattern="invoice",
            matches=1,
            matched=1,
            value="INV-001",
        )
    ]

    question_result = QuestionCoverage(
        generated=2,
        skipped=1,
        generated_fields=['invoice_number', 'amount'],
        missing_fields=['customer'],
    )

    summary = DocumentSummaryAnalyzer.analyze(
        classified,
        field_result,
        regex_result,
        question_result,
    )

    assert summary.filename == "Invoice.pdf"
    assert summary.document_type == "Invoice"

    assert summary.generated_questions == 2
    assert summary.skipped_questions == 1

    assert summary.field_coverage == 2 / 3

    assert summary.extracted_fields == [
        "invoice_number",
        "amount",
    ]

    assert summary.missing_fields == [
        "customer",
    ]

    assert len(summary.regex_stats) == 1
