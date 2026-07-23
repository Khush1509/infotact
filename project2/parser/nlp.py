"""NLP and Regex rule engine for contract paragraph categorization and governing law jurisdiction extraction.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


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
    def process_paragraph(
        cls,
        text: str,
        clause_number: Optional[str] = None,
        evaluate_risk: bool = True
    ) -> Dict[str, Any]:
        """Categorize paragraph, extract jurisdiction, and evaluate legal risks.

        Args:
            text (str): Clause text.
            clause_number (Optional[str]): Optional clause identifier.
            evaluate_risk (bool): Whether to run risk evaluation. Defaults to True.

        Returns:
            Dict containing 'clause_number', 'text', 'category', 'jurisdiction', and 'risk_evaluation'.
        """
        category = cls.categorize_paragraph(text)
        jurisdiction = None

        if category == cls.GOVERNING_LAW or "governed by" in text.lower() or "laws of" in text.lower():
            jurisdiction = cls.extract_governing_jurisdiction(text)

        result: Dict[str, Any] = {
            "clause_number": clause_number,
            "text": text,
            "category": category,
            "jurisdiction": jurisdiction,
        }

        if evaluate_risk:
            risk_eval = RiskEvaluator.evaluate_paragraph(text)
            result["risk_evaluation"] = risk_eval

        return result


class RiskEvaluator:
    """Evaluates contract text (paragraphs and sentences) for legal risks using rule-based NLP engines."""

    # Risk Flag Types
    UNLIMITED_INDEMNITY = "UNLIMITED_INDEMNITY"
    UNLIMITED_LIABILITY = "UNLIMITED_LIABILITY"
    UNILATERAL_TERMINATION = "UNILATERAL_TERMINATION"
    PERPETUAL_CONFIDENTIALITY = "PERPETUAL_CONFIDENTIALITY"
    CLASS_ACTION_WAIVER = "CLASS_ACTION_WAIVER"
    FOREIGN_JURISDICTION = "FOREIGN_JURISDICTION"
    UNILATERAL_MODIFICATION = "UNILATERAL_MODIFICATION"
    SEVERE_PENALTY = "SEVERE_PENALTY"
    BROAD_IP_TRANSFER = "BROAD_IP_TRANSFER"

    # Risk Rule Definitions
    RISK_RULES = [
        {
            "type": UNLIMITED_INDEMNITY,
            "patterns": [
                r"\bindemnify.*without\s+limit\b",
                r"\bunlimited\s+indemnification\b",
                r"\bindemnify\s+(?:and\s+hold\s+harmless\s+)?against\s+any\s+and\s+all\s+(?:claims|losses|damages)\b",
                r"\bindemnify.*for\s+all\s+direct\s+and\s+indirect\s+losses\b",
                r"\bhold\s+harmless\s+from\s+any\s+and\s+all\b",
            ],
            "description": "Clause contains uncapped or broad indemnification obligations.",
            "base_score": 0.90,
        },
        {
            "type": UNLIMITED_LIABILITY,
            "patterns": [
                r"\bno\s+(?:limitation|limit|cap)\s+(?:on|of)\s+liability\b",
                r"\bliability\s+shall\s+be\s+unlimited\b",
                r"\bshall\s+be\s+liable\s+for\s+any\s+and\s+all\s+damages\b",
                r"\bwithout\s+limitation\s+of\s+liability\b",
                r"\bwaive[s]?\s+any\s+limitation\s+of\s+liability\b",
            ],
            "description": "Clause removes or lacks liability caps, exposing the entity to unlimited liability.",
            "base_score": 0.95,
        },
        {
            "type": UNILATERAL_TERMINATION,
            "patterns": [
                r"\bterminate\s+at\s+any\s+time\s+without\s+cause\b",
                r"\bterminate\s+immediately\s+without\s+notice\b",
                r"\bimmediate\s+termination\s+without\s+prior\s+notice\b",
                r"\bsole\s+discretion\s+to\s+terminate\b",
                r"\bterminate\s+for\s+convenience\s+without\s+notice\b",
            ],
            "description": "Allows unilateral termination without cause or notice.",
            "base_score": 0.85,
        },
        {
            "type": PERPETUAL_CONFIDENTIALITY,
            "patterns": [
                r"\bconfidentiality\s+obligations?\s+shall\s+survive\s+(?:in\s+perpetuity|indefinitely|forever)\b",
                r"\bkeep\s+confidential\s+in\s+perpetuity\b",
                r"\bsurvive\s+termination\s+indefinitely\b",
                r"\bconfidentiality\s+without\s+(?:time\s+)?limit\b",
            ],
            "description": "Imposes perpetual or indefinite confidentiality obligations.",
            "base_score": 0.75,
        },
        {
            "type": CLASS_ACTION_WAIVER,
            "patterns": [
                r"\bwaive[s]?\s+(?:any\s+)?right\s+to\s+participate\s+in\s+a\s+class\s+action\b",
                r"\bclass\s+action\s+waiver\b",
                r"\bno\s+class\s+action\b",
            ],
            "description": "Contains a waiver of class action litigation rights.",
            "base_score": 0.80,
        },
        {
            "type": UNILATERAL_MODIFICATION,
            "patterns": [
                r"\breserves\s+the\s+right\s+to\s+(?:modify|amend|change)\s+this\s+agreement\s+at\s+any\s+time\b",
                r"\bmodify\s+(?:these\s+)?terms\s+without\s+(?:prior\s+)?notice\b",
                r"\bsole\s+discretion\s+to\s+(?:change|amend)\b",
            ],
            "description": "Allows one party to unilaterally modify contract terms without consent.",
            "base_score": 0.85,
        },
        {
            "type": SEVERE_PENALTY,
            "patterns": [
                r"\blate\s+fee\s+of\s+(?:[2-9]\d|\d{3})%\b",
                r"\bpenalty\s+interest\s+rate\s+of\b",
                r"\bliquidated\s+damages\s+of\s+\$\d{5,}\b",
            ],
            "description": "Clause specifies severe financial penalties or high late fees.",
            "base_score": 0.80,
        },
        {
            "type": BROAD_IP_TRANSFER,
            "patterns": [
                r"\birrevocably\s+assigns?\s+all\s+(?:right,?\s+title,?\s+and\s+interest|intellectual\s+property)\b",
                r"\bassigns?\s+all\s+pre-existing\s+(?:ip|intellectual\s+property)\b",
                r"\bwork\s+made\s+for\s+hire\s+transferring\s+all\s+rights\b",
            ],
            "description": "Broad or irrevocable assignment of intellectual property rights.",
            "base_score": 0.85,
        },
    ]

    @classmethod
    def split_sentences(cls, text: str) -> List[str]:
        """Split paragraph text into individual sentences for sentence-level risk scanning.

        Args:
            text (str): Full paragraph text.

        Returns:
            List[str]: List of extracted non-empty sentence strings.
        """
        if not text or not text.strip():
            return []
        # Split on sentence boundary punctuation (. ! ?) followed by space or newline
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        return [s.strip() for s in sentences if s.strip()]

    @classmethod
    def evaluate_sentence(cls, sentence: str) -> List[Dict[str, Any]]:
        """Evaluate a single sentence against risk rules.

        Args:
            sentence (str): Sentence text.

        Returns:
            List[Dict[str, Any]]: List of triggered risk flags for this sentence.
        """
        if not sentence or not sentence.strip():
            return []

        flags = []
        sentence_lower = sentence.lower()

        for rule in cls.RISK_RULES:
            for pattern in rule["patterns"]:
                if re.search(pattern, sentence_lower, re.IGNORECASE):
                    flags.append({
                        "flag_type": rule["type"],
                        "description": rule["description"],
                        "confidence_score": rule["base_score"],
                        "matched_text": sentence.strip(),
                    })
                    break  # Prevent duplicate flag of same type for the same sentence

        return flags

    @classmethod
    def evaluate_paragraph(cls, text: str) -> Dict[str, Any]:
        """Iterate through extracted paragraph and its sentences to evaluate risk.

        Args:
            text (str): Full paragraph text.

        Returns:
            Dict containing 'has_risk', 'overall_risk_score', 'risk_level', and 'risk_flags'.
        """
        if not text or not text.strip():
            return {
                "has_risk": False,
                "overall_risk_score": 0.0,
                "risk_level": "LOW",
                "risk_flags": [],
            }

        sentences = cls.split_sentences(text)
        all_flags: List[Dict[str, Any]] = []

        # Iterate through each extracted sentence to evaluate risk
        for sentence in sentences:
            sentence_flags = cls.evaluate_sentence(sentence)
            all_flags.extend(sentence_flags)

        # Fallback paragraph-level check if sentence split missed pattern
        if not all_flags:
            paragraph_flags = cls.evaluate_sentence(text)
            all_flags.extend(paragraph_flags)

        if not all_flags:
            return {
                "has_risk": False,
                "overall_risk_score": 0.0,
                "risk_level": "LOW",
                "risk_flags": [],
            }

        max_score = max(f["confidence_score"] for f in all_flags)
        if max_score >= 0.85:
            risk_level = "HIGH"
        elif max_score >= 0.70:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "has_risk": True,
            "overall_risk_score": max_score,
            "risk_level": risk_level,
            "risk_flags": all_flags,
        }

