"""NLP and Regex rule engine for contract paragraph categorization and governing law jurisdiction extraction.
"""

import re
from typing import Dict, Optional, Tuple


class ClauseCategorizer:
    """Categorizes contract paragraphs into legal categories and extracts governing law jurisdictions."""

    # Category Constants
    GOVERNING_LAW = "GOVERNING_LAW"
    CONFIDENTIALITY = "CONFIDENTIALITY"
    TERMINATION = "TERMINATION"
    INDEMNIFICATION = "INDEMNIFICATION"
    LIMITATION_OF_LIABILITY = "LIMITATION_OF_LIABILITY"
    DISPUTE_RESOLUTION = "DISPUTE_RESOLUTION"
    INTELLECTUAL_PROPERTY = "INTELLECTUAL_PROPERTY"
    PAYMENT = "PAYMENT"
    FORCE_MAJEURE = "FORCE_MAJEURE"
    GENERAL = "GENERAL"

    # Category Rule Definitions (Regex Patterns & Key Terms)
    CATEGORY_PATTERNS = {
        GOVERNING_LAW: [
            r"\bgoverning\s+law\b",
            r"\bchoice\t*of\s+law\b",
            r"\bgoverned\s+by\b",
            r"\bconstrued\s+in\s+accordance\s+with\s+(?:the\s+)?laws\b",
            r"\bjurisdiction\s+of\s+the\s+courts\b",
            r"\bsubject\s+to\s+the\s+laws\s+of\b",
            r"\bvenue\s+for\s+any\s+action\b",
        ],
        CONFIDENTIALITY: [
            r"\bconfidential\s+information\b",
            r"\bnon-disclosure\b",
            r"\bproprietary\s+information\b",
            r"\bkeep\s+confidential\b",
            r"\bconfidentiality\s+obligations\b",
            r"\bconfidentiality\b",
            r"\bconfidential\b",
        ],
        TERMINATION: [
            r"\bterm\s+and\s+termination\b",
            r"\bright\s+to\s+terminate\b",
            r"\bnotice\s+of\s+termination\b",
            r"\bexpiration\s+or\s+termination\b",
            r"\bterminate\s+this\s+agreement\b",
        ],
        INDEMNIFICATION: [
            r"\bindemnify\b",
            r"\bindemnification\b",
            r"\bhold\s+harmless\b",
            r"\bdefend\s+and\s+hold\b",
        ],
        LIMITATION_OF_LIABILITY: [
            r"\blimitation\s+of\s+liability\b",
            r"\bin\s+no\s+event\s+shall\b",
            r"\bconsequential\s+damages\b",
            r"\baggregate\s+liability\b",
            r"\bindirect\s*,?\s*incidental\s*,?\s*or\s*punitive\s+damages\b",
        ],
        DISPUTE_RESOLUTION: [
            r"\bdispute\s+resolution\b",
            r"\barbitration\b",
            r"\bmediat(?:e|ion)\b",
            r"\bbinding\s+arbitration\b",
            r"\bclass\s+action\s+waiver\b",
        ],
        INTELLECTUAL_PROPERTY: [
            r"\bintellectual\s+property\b",
            r"\btrademarks?\b",
            r"\bpatents?\b",
            r"\bcopyrights?\b",
            r"\bwork\s+made\s+for\s+hire\b",
            r"\bownership\s+of\s+(?:ip|deliverables|materials)\b",
        ],
        PAYMENT: [
            r"\bpayment\s+terms\b",
            r"\binvoic(?:e|ing)\b",
            r"\bfees\s+and\s+expenses\b",
            r"\bpayment\s+shall\s+be\s+made\b",
            r"\blate\s+payment\b",
        ],
        FORCE_MAJEURE: [
            r"\bforce\s+majeure\b",
            r"\bacts?\s+of\s+god\b",
            r"\bunforeseeable\s+circumstances\b",
            r"\beyond\s+(?:the\s+)?reasonable\s+control\b",
        ],
    }

    # Known jurisdictions for regex extraction & fallback matching
    KNOWN_JURISDICTIONS = [
        "New York",
        "Delaware",
        "California",
        "England and Wales",
        "Texas",
        "Illinois",
        "Massachusetts",
        "Florida",
        "Nevada",
        "Washington",
        "New Jersey",
        "Pennsylvania",
        "Georgia",
        "Virginia",
        "Ontario",
        "United Kingdom",
        "Germany",
        "France",
        "Singapore",
        "Japan",
        "Australia",
        "Canada",
        "State of New York",
        "State of Delaware",
        "State of California",
        "State of Texas",
        "Commonwealth of Massachusetts",
        "Commonwealth of Virginia",
        "Commonwealth of Pennsylvania",
    ]

    # Regex patterns for isolation of Governing Law Jurisdiction
    JURISDICTION_PATTERNS = [
        # Pattern 1: governed by / construed in accordance with the laws of (the) [State of X / Jurisdiction]
        r"(?:governed\s+by|construed\s+in\s+accordance\s+with|interpreted\s+under|subject\s+to)\s+(?:and\s+[a-z\s]+)*?(?:the\s+)?laws\s+of\s+(?:the\s+)?(State\s+of\s+[A-Z][a-zA-Z\s]+|Commonwealth\s+of\s+[A-Z][a-zA-Z\s]+|[A-Z][a-zA-Z\s]+(?:\s+and\s+[A-Z][a-zA-Z\s]+)?)",
        # Pattern 2: exclusive jurisdiction of (the courts of) [Jurisdiction]
        r"(?:exclusive\s+)?jurisdiction\s+of\s+(?:the\s+)?(?:courts\s+of\s+|courts\s+located\s+in\s+)?(?:the\s+)?(State\s+of\s+[A-Z][a-zA-Z\s]+|Commonwealth\s+of\s+[A-Z][a-zA-Z\s]+|[A-Z][a-zA-Z\s]+(?:\s+and\s+[A-Z][a-zA-Z\s]+)?)",
        # Pattern 3: laws of the State of [State] / Commonwealth of [State]
        r"laws\s+of\s+(?:the\s+)?(State\s+of\s+[A-Z][a-zA-Z\s]+|Commonwealth\s+of\s+[A-Z][a-zA-Z\s]+)",
        # Pattern 4: laws of [Jurisdiction]
        r"laws\s+of\s+(?:the\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
    ]

    @classmethod
    def categorize_paragraph(cls, text: str) -> str:
        """Categorize a text paragraph using rule-based Regex pattern matching.

        Args:
            text (str): The text of the clause or paragraph.

        Returns:
            str: Category constant name (e.g. 'GOVERNING_LAW', 'CONFIDENTIALITY', etc.)
        """
        if not text or not text.strip():
            return cls.GENERAL

        text_lower = text.lower()

        # Score matching categories
        category_scores: Dict[str, int] = {}

        for category, patterns in cls.CATEGORY_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    score += len(matches) * 2

            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return cls.GENERAL

        # Return category with highest score
        best_category = max(category_scores, key=category_scores.get)
        return best_category

    @classmethod
    def extract_governing_jurisdiction(cls, text: str) -> Optional[str]:
        """Isolate and extract the governing law jurisdiction from paragraph text.

        Args:
            text (str): Clause text.

        Returns:
            Optional[str]: Extracted jurisdiction (e.g., 'State of New York', 'Delaware', 'England and Wales'), or None.
        """
        if not text or not text.strip():
            return None

        # Clean text whitespace
        clean_text = " ".join(text.split())

        # Attempt extraction via regex patterns
        for pattern in cls.JURISDICTION_PATTERNS:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                raw_jurisdiction = match.group(1).strip()
                cleaned = cls._clean_jurisdiction(raw_jurisdiction)
                if cleaned:
                    return cleaned

        # Fallback check against known jurisdictions if text contains governing law phrases
        for kj in cls.KNOWN_JURISDICTIONS:
            pattern = r"\b" + re.escape(kj) + r"\b"
            if re.search(pattern, clean_text, re.IGNORECASE):
                return kj

        return None

    @classmethod
    def _clean_jurisdiction(cls, raw: str) -> Optional[str]:
        """Clean and normalize raw extracted jurisdiction text."""
        if not raw:
            return None

        # Remove trailing clauses / noise words
        noise_words = [
            r"\bwithout\s+regard.*$",
            r"\bwithout\s+giving\s+effect.*$",
            r"\bexcluding.*$",
            r"\bapplicable\s+to.*$",
            r"\bthereof.*$",
            r"\bherein.*$",
            r"\band\s+the\s+courts.*$",
            r"\bexclusive\s+of.*$",
        ]
        cleaned = raw
        for nw in noise_words:
            cleaned = re.sub(nw, "", cleaned, flags=re.IGNORECASE).strip()

        # Trim punctuation
        cleaned = cleaned.strip(" .,;:\"'()")

        # If string is empty or too short / long, reject
        if not cleaned or len(cleaned) < 2 or len(cleaned) > 80:
            return None

        # Standardize capitalization if not already formatted
        words = cleaned.split()
        capitalized_words = []
        for word in words:
            if word.lower() in ("of", "and", "in", "the", "for", "to"):
                capitalized_words.append(word.lower())
            else:
                capitalized_words.append(word.capitalize())

        final_val = " ".join(capitalized_words)
        # Ensure state of ... starts capitalized
        if final_val.lower().startswith("state of "):
            final_val = "State of " + final_val[9:]
        elif final_val.lower().startswith("commonwealth of "):
            final_val = "Commonwealth of " + final_val[16:]

        return final_val

    @classmethod
    def process_paragraph(cls, text: str, clause_number: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Categorize paragraph and extract jurisdiction if applicable.

        Args:
            text (str): Clause text.
            clause_number (Optional[str]): Optional clause identifier.

        Returns:
            Dict containing 'category' and 'jurisdiction'.
        """
        category = cls.categorize_paragraph(text)
        jurisdiction = None

        if category == cls.GOVERNING_LAW or "governed by" in text.lower() or "laws of" in text.lower():
            jurisdiction = cls.extract_governing_jurisdiction(text)

        return {
            "clause_number": clause_number,
            "text": text,
            "category": category,
            "jurisdiction": jurisdiction,
        }
