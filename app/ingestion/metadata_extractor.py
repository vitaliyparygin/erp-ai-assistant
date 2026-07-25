import re
from app.parsers.field_dictionary import FIELD_DEFINITIONS

# PASSPORT_PATTERNS = [
#     r"passport\s*(?:id|number|no\.?)?\s*[:#]?\s*([A-Z]{2}\d{6})",
#
#     r"паспорт\s*(?:серії)?\s*([А-ЯІЇЄ]{2})\s*№?\s*(\d{6})",
#
#     r"серії\s*([А-ЯІЇЄ]{2})\s*№?\s*(\d{6})",
# ]

class MetadataExtractor:

    @staticmethod
    def extract(text: str, filename: str) -> dict:
        metadata = {
            "document_name": filename,
        }
        text_lower = text.lower()
        if (
            "service agreement" in text_lower
            or "contract number" in text_lower
            or "договір" in text_lower
            or "agreement" in text_lower
            or "договор" in text_lower
        ):
            metadata["document_type"] = "contract"
        elif "invoice" in text_lower:
            metadata["document_type"] = "invoice"

        elif "opportunity" in text_lower:
            metadata["document_type"] = "opportunity"
        print(type(FIELD_DEFINITIONS))
        print(FIELD_DEFINITIONS)
        print(type(FIELD_DEFINITIONS["invoice_number"]))
        for field, definition in FIELD_DEFINITIONS.items():
            for pattern in definition.patterns:
                m = re.search(
                    pattern,
                    text,
                    re.IGNORECASE | re.MULTILINE,
                )
                if not m:
                    continue
                if m.lastindex:
                    value = m.group(1)
                else:
                    value = m.group(0)
                metadata[definition.name] = value.strip()
                break
        return metadata
