import re
from app.parsers.field_dictionary import FIELD_DEFINITIONS
from rules import detect_document_type

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

        document_type = detect_document_type(
            text=text_lower,
            filename=filename,
        )

        if document_type:
            metadata["document_type"] = document_type

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
