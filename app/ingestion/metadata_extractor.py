import re


class MetadataExtractor:

    @staticmethod
    def extract(text: str, filename: str) -> dict:
        print(f"MetadataExtractor start {filename}" )

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



        #
        # document type
        #

        # if "contract" in lower_name:
        #     metadata["document_type"] = "contract"
        #
        # elif "agreement" in lower_name:
        #     metadata["document_type"] = "contract"
        #
        # elif "invoice" in lower_name:
        #     metadata["document_type"] = "invoice"
        #
        # elif "opportunity" in lower_name:
        #     metadata["document_type"] = "opportunity"

        #
        # contract number
        #

        m = re.search(
            r"Contract Number:\s*([A-Z0-9\-]+)",
            text,
            re.IGNORECASE,
        )

        if m:
            metadata["contract_number"] = m.group(1)

        #
        # valid until
        #

        m = re.search(
            r"Valid Until:\s*([0-9\-]+)",
            text,
            re.IGNORECASE,
        )

        if m:
            metadata["valid_until"] = m.group(1)

        #
        # customer
        #

        m = re.search(
            r"Customer:\s*(.+)",
            text,
            re.IGNORECASE,
        )

        if m:
            metadata["customer"] = m.group(1).strip()

        #
        # contractor
        #

        m = re.search(
            r"Contractor:\s*(.+)",
            text,
            re.IGNORECASE,
        )

        if m:
            metadata["contractor"] = m.group(1).strip()

        #
        # CRM stage
        #

        m = re.search(
            r"Stage:\s*(.+)",
            text,
            re.IGNORECASE,
        )

        if m:
            metadata["stage"] = m.group(1).strip()
        print('MetadataExtractor.metadata:')
        print(metadata)
        return metadata