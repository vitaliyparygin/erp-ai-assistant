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
        print(f"MetadataExtractor start " )

        metadata = {
            "document_name": filename,
        }

        # lower_name = filename.lower()
        text_lower = text.lower()
        print('1111111-MetadataExtractor-111111')
        print(text_lower)

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

        for field, definition in FIELD_DEFINITIONS.items():

            for pattern in definition["patterns"]:

                m = re.search(
                    pattern,
                    text,
                    re.IGNORECASE | re.MULTILINE,
                )

                if not m:
                    continue

                # якщо є група захоплення
                if m.lastindex:
                    value = m.group(1)

                else:
                    value = m.group(0)

                metadata[field] = value.strip()

                break

        print('MetadataExtractor.metadata:')
        print(metadata)
        return metadata
