from rules.loader import load_template
from rules.models import FieldRule
from functools import cache

ERP_TEMPLATE = load_template("erp")


def classification_rules():
    return ERP_TEMPLATE.classification_rules


def extraction_rules():
    return ERP_TEMPLATE.extraction_rules


@cache
def erp_template():
    return load_template("erp")


def flat_extraction_rules() -> dict[str, FieldRule]:
    result: dict[str, FieldRule] = {}

    for rules in ERP_TEMPLATE.extraction_rules.values():
        for rule in rules:
            result[rule.name] = rule

    return result
