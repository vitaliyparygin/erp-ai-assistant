"""Tests for rag_benchmark.extractor."""

from __future__ import annotations
import pytest
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
    def __init__(self, name, patterns):
        self.name = name
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
    result = SimpleNamespace(
        expected_fields=[
            "vendor",
            "amount",
            "date",
        ],
        questions=[
            object(),
            object(),
        ],
    )

    coverage = QuestionCoverageAnalyzer.analyze(result)

    assert coverage.expected == 3
    assert coverage.generated == 2
    assert coverage.coverage == pytest.approx(2 / 3)


def test_document_summary():
    inspect = SimpleNamespace(
        classified=SimpleNamespace(
            classification=SimpleNamespace(
                document_type="Invoice",
            ),
            document=SimpleNamespace(
                filename="Invoice.pdf",
            ),
            metadata=SimpleNamespace(
                fields={
                    "invoice_number": "INV-001",
                    "amount": "100",
                },
            ),
        ),

        missing_fields=[
            "customer",
        ],

        regex_stats=[],

        field_coverage=SimpleNamespace(
            coverage=2 / 3,
        ),

        question_coverage=SimpleNamespace(
            expected=3,
            generated=2,
            coverage=2 / 3,
        ),
    )
