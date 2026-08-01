"""NLP and Regex rule engine for contract paragraph categorization and governing law jurisdiction extraction.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import spacy
    _SPACY_AVAILABLE = True
except ImportError:
    spacy = None
    _SPACY_AVAILABLE = False


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
        best_category = max(category_scores, key=lambda k: category_scores[k])
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

        entities = ContractEntityExtractor.extract_entities(text)
        duration_term = ContractDurationTermExtractor.analyze_duration_and_termination(text)

        result: Dict[str, Any] = {
            "clause_number": clause_number,
            "text": text,
            "category": category,
            "jurisdiction": jurisdiction,
            "entities": entities,
            "duration_and_termination": duration_term,
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
    DANGEROUS_JARGON = "DANGEROUS_JARGON"

    # Risk Rule Definitions
    RISK_RULES: List[Dict[str, Any]] = [
        {
            "type": UNLIMITED_INDEMNITY,
            "patterns": [
                r"\bindemnify.*without\s+limit\b",
                r"\bunlimited\s+indemnification\b",
                r"\bindemnify\s+(?:and\s+hold\s+harmless\s+)?against\s+any\s+and\s+all\s+(?:claims|losses|damages)\b",
                r"\bindemnify.*for\s+all\s+direct\s+and\s+indirect\s+losses\b",
                r"\bhold\s+harmless\s+from\s+any\s+and\s+all\b",
                r"\bindemnify\b",
                r"\bindemnification\b",
                r"\bhold\s+harmless\b",
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
                r"\bunlimited\s+liability\b",
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
        {
            "type": DANGEROUS_JARGON,
            "patterns": [
                r"\bexclusive\b",
                r"\bsole\s+and\s+exclusive\b",
                r"\bexclusive\s+(?:remedy|jurisdiction|right|license|grant)\b",
                r"\bunlimited\s+liability\b",
                r"\bindemnify\b",
            ],
            "description": "Sentence contains dangerous legal jargon (e.g., indemnify, unlimited liability, exclusive terms).",
            "base_score": 0.80,
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
            patterns: List[str] = rule["patterns"]
            for pattern in patterns:
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


class ContractEntityExtractor:
    """Extracts contracting parties (counterparty names) and signing/effective dates using spaCy NER and Regex rules."""

    _nlp_model = None
    _model_loaded = False

    @classmethod
    def get_nlp_model(cls):
        """Lazy load spaCy model with graceful fallback if unavailable."""
        if not cls._model_loaded:
            cls._model_loaded = True
            if _SPACY_AVAILABLE:
                try:
                    cls._nlp_model = spacy.load("en_core_web_sm")
                except Exception:
                    try:
                        cls._nlp_model = spacy.blank("en")
                    except Exception:
                        cls._nlp_model = None
            else:
                cls._nlp_model = None
        return cls._nlp_model

    @classmethod
    def extract_parties(cls, text: str) -> List[str]:
        """Extract key contracting parties (counterparty names) from contract text.

        Args:
            text (str): Contract preamble or full text.

        Returns:
            List[str]: List of extracted party names.
        """
        if not text or not text.strip():
            return []

        parties: List[str] = []
        nlp = cls.get_nlp_model()

        # 1. spaCy NER entity extraction
        if nlp is not None and hasattr(nlp, "pipe_names") and "ner" in nlp.pipe_names:
            doc = nlp(text[:15000])
            for ent in doc.ents:
                if ent.label_ in ("ORG", "PERSON"):
                    name = ent.text.strip()
                    cleaned = cls._clean_party_name(name)
                    if cleaned and cls._is_valid_party_name(cleaned) and cleaned not in parties:
                        parties.append(cleaned)

        # 2. Regex patterns for party preambles and definitions
        party_regexes = [
            r"(?:by\s+and\s+)?between\s+([A-Z0-9][A-Za-z0-9\s,\.\&\'-]+?)\s+(?:\([^\)]+\)\s+)?and\s+([A-Z0-9][A-Za-z0-9\s,\.\&\'-]+?)(?:\s*,|\s*\(|\s+hereinafter|\s+dated|\s*$)",
            r"([A-Z0-9][A-Za-z0-9\s,\.\&\'-]{2,60})\s*\(\s*[\"'](?:Company|Client|Provider|Vendor|Customer|Contractor|Buyer|Seller|Licensor|Licensee|Party\s+[AB])[\"']\s*\)",
            r"([A-Z0-9][A-Za-z0-9\s,\.\&\'-]{2,60})\s*,\s*(?:a\s+[A-Za-z\s]+(?:corporation|limited\s+liability\s+company|llc|inc|co|company)?,?\s*)?hereinafter",
        ]

        for pat in party_regexes:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                for grp in m.groups():
                    if grp:
                        clean_p = cls._clean_party_name(grp)
                        if clean_p and cls._is_valid_party_name(clean_p) and clean_p not in parties:
                            parties.append(clean_p)

        return parties

    @classmethod
    def _clean_party_name(cls, raw: str) -> str:
        """Clean and normalize raw extracted party string."""
        if not raw:
            return ""
        name = raw.strip()
        name = re.sub(
            r"^(?:this\s+agreement\s+(?:is\s+)?entered\s+into\s+by\s+and\s+between|entered\s+into\s+by\s+and\s+between|by\s+and\s+between|between)\s+",
            "", name, flags=re.IGNORECASE
        )
        noise_patterns = [
            r"\s*\bhereinafter.*$",
            r"\s*\b(?:each\s+a|collectively|individually).*$",
            r"\s*\(?\b(?:a|an)\s+(?:State\s+of\s+)?\w+\s+(?:corporation|limited\s+liability\s+company|llc|inc|co|company)\b.*$",
            r"\s*,?\s*having\s+its\s+principal\s+place\s+of\s+business.*$",
            r"\s*,?\s*a\s+corporation\b.*$",
        ]
        for n in noise_patterns:
            name = re.sub(n, "", name, flags=re.IGNORECASE).strip()
        return name.strip(" .,;:\"'()")

    @classmethod
    def _is_valid_party_name(cls, name: str) -> bool:
        """Check if extracted candidate string represents a valid party name."""
        if not name or len(name) < 2 or len(name) > 100:
            return False
        invalid_words = {
            "this agreement", "agreement", "party", "parties", "witnesseth",
            "whereas", "section", "article", "exhibit", "schedule", "the laws",
            "state of", "commonwealth of"
        }
        if name.lower() in invalid_words:
            return False
        return True

    @classmethod
    def extract_dates(cls, text: str) -> Dict[str, Any]:
        """Extract signing dates, effective dates, and execution dates from contract text.

        Args:
            text (str): Contract text.

        Returns:
            Dict containing 'signing_dates', 'effective_date', and 'all_dates'.
        """
        if not text or not text.strip():
            return {"signing_dates": [], "effective_date": None, "all_dates": []}

        all_dates: List[str] = []
        signing_dates: List[str] = []
        effective_date: Optional[str] = None

        nlp = cls.get_nlp_model()
        if nlp is not None and hasattr(nlp, "pipe_names") and "ner" in nlp.pipe_names:
            doc = nlp(text[:15000])
            for ent in doc.ents:
                if ent.label_ == "DATE":
                    d_str = ent.text.strip()
                    if d_str and d_str not in all_dates:
                        all_dates.append(d_str)

        # Explicit effective date patterns
        effective_patterns = [
            r"\beffective\s+(?:as\s+of\s+)?([A-Za-z]+\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
            r"\bdated\s+as\s+of\s+([A-Za-z]+\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
            r"\bcommenc(?:es|ing)\s+on\s+([A-Za-z]+\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
        ]
        for pat in effective_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                effective_date = m.group(1).strip()
                break

        # Explicit signing date patterns
        signing_patterns = [
            r"\bsigned\s+(?:on|this)?\s*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
            r"\bexecuted\s+(?:on|this)?\s*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
            r"\bthis\s+(\d{1,2}(?:st|nd|rd|th)?)\s+day\s+of\s+([A-Za-z]+),\s*(\d{4})",
            r"\bdate:\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
        ]
        for pat in signing_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                if len(m.groups()) == 3:
                    formatted = f"{m.group(2)} {m.group(1)}, {m.group(3)}"
                    if formatted not in signing_dates:
                        signing_dates.append(formatted)
                elif m.group(1):
                    d = m.group(1).strip()
                    if d not in signing_dates:
                        signing_dates.append(d)

        # Fallback date regex if spaCy returned nothing
        if not all_dates:
            general_date_pat = r"\b([A-Za-z]{3,9}\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})\b"
            for m in re.finditer(general_date_pat, text):
                d_str = m.group(1).strip()
                if d_str not in all_dates:
                    all_dates.append(d_str)

        for d in signing_dates:
            if d not in all_dates:
                all_dates.append(d)
        if effective_date and effective_date not in all_dates:
            all_dates.append(effective_date)

        return {
            "signing_dates": signing_dates,
            "effective_date": effective_date,
            "all_dates": all_dates,
        }

    @classmethod
    def extract_entities(cls, text: str) -> Dict[str, Any]:
        """Extract all key entities (counterparties and dates)."""
        parties = cls.extract_parties(text)
        date_data = cls.extract_dates(text)
        return {
            "parties": parties,
            "signing_dates": date_data["signing_dates"],
            "effective_date": date_data["effective_date"],
            "all_dates": date_data["all_dates"],
        }


class ContractDurationTermExtractor:
    """Identifies and extracts contract duration (term length, renewal) and termination clauses."""

    @classmethod
    def extract_duration(cls, text: str) -> Dict[str, Any]:
        """Extract contract term duration length and auto-renewal conditions.

        Args:
            text (str): Contract clause or document text.

        Returns:
            Dict containing 'term_length', 'auto_renewal', 'renewal_term', and 'duration_clause_text'.
        """
        if not text or not text.strip():
            return {
                "term_length": None,
                "auto_renewal": False,
                "renewal_term": None,
                "duration_clause_text": None,
            }

        term_length: Optional[str] = None
        auto_renewal = False
        renewal_term: Optional[str] = None
        duration_clause_text: Optional[str] = None

        # Term length patterns
        term_patterns = [
            r"\b(?:initial\s+term|term\s+of|period\s+of)\b(?:\s+[a-z\s]{1,30})?\s+([0-9]+\s+(?:years?|months?|days?)|one|two|three|four|five|six|seven|eight|nine|ten\s+(?:years?|months?))",
            r"\b(?:initial\s+term\s+of|term\s+of|period\s+of|shall\s+be)\s+([0-9]+\s+(?:years?|months?|days?)|one|two|three|four|five|six|seven|eight|nine|ten\s+(?:years?|months?))",
            r"\b([0-9]+\s*(?:-\s*)?(?:year|month|day))\s+(?:initial\s+)?(?:term|period|duration)\b",
            r"\bcontinue\s+in\s+force\s+for\s+(?:a\s+period\s+of\s+)?([0-9]+\s+(?:years?|months?|days?)|one|two|three|four|five\s+(?:years?|months?))",
            r"\bfor\s+a\s+term\s+commencing\s+on\s+[^,;\n]+\s+and\s+ending\s+on\s+([A-Za-z]+\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
        ]
        for pat in term_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                term_length = m.group(1).strip()
                break

        # Auto-renewal check
        if re.search(r"\bauto(?:matically)?\s+renew(?:s|al)?\b", text, re.IGNORECASE) or re.search(r"\bsuccessive\s+(?:term|period)s?\b", text, re.IGNORECASE):
            auto_renewal = True

        renewal_patterns = [
            r"\bsuccessive\s+(?:periods?|terms?)\s+of\s+([0-9]+\s+(?:years?|months?|days?)|one|two|three\s+(?:years?|months?))",
            r"\brenew\s+for\s+(?:additional\s+)?(?:terms?|periods?)\s+of\s+([0-9]+\s+(?:years?|months?|days?)|one|two|three\s+(?:years?|months?))",
            r"\badditional\s+([0-9]+\s*(?:-\s*)?(?:year|month|day))\s+(?:terms?|periods?)\b",
        ]
        for pat in renewal_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                renewal_term = m.group(1).strip()
                break

        if term_length or auto_renewal:
            duration_clause_text = text.strip()

        return {
            "term_length": term_length,
            "auto_renewal": auto_renewal,
            "renewal_term": renewal_term,
            "duration_clause_text": duration_clause_text,
        }

    @classmethod
    def extract_termination_clauses(cls, text: str) -> Dict[str, Any]:
        """Extract termination conditions, notice periods, and termination grounds.

        Args:
            text (str): Contract clause or text.

        Returns:
            Dict containing 'notice_period', 'termination_types', 'has_convenience_termination',
            'has_cause_termination', and 'termination_clause_text'.
        """
        if not text or not text.strip():
            return {
                "notice_period": None,
                "termination_types": [],
                "has_convenience_termination": False,
                "has_cause_termination": False,
                "termination_clause_text": None,
            }

        notice_period: Optional[str] = None
        termination_types: List[str] = []
        has_convenience = False
        has_cause = False

        # Notice period pattern
        notice_pat = r"([0-9]+|\bthirty\b|\bsixty\b|\bninety\b|\bfifteen\b)\s*(?:\([0-9]+\)\s*)?days?['’]?\s+(?:prior\s+)?(?:written\s+)?notice"
        m_notice = re.search(notice_pat, text, re.IGNORECASE)
        if m_notice:
            notice_period = f"{m_notice.group(1)} days"

        if re.search(r"\bwithout\s+cause\b|\bfor\s+convenience\b", text, re.IGNORECASE):
            has_convenience = True
            termination_types.append("TERMINATION_FOR_CONVENIENCE")

        if re.search(r"\bfor\s+cause\b|\bmaterial\s+breach\b|\bdefault\b", text, re.IGNORECASE):
            has_cause = True
            termination_types.append("TERMINATION_FOR_CAUSE")

        if re.search(r"\bimmediate\s+termination\b|\bterminate\s+immediately\b", text, re.IGNORECASE):
            termination_types.append("IMMEDIATE_TERMINATION")

        termination_clause_text = text.strip() if (termination_types or notice_period) else None

        return {
            "notice_period": notice_period,
            "termination_types": termination_types,
            "has_convenience_termination": has_convenience,
            "has_cause_termination": has_cause,
            "termination_clause_text": termination_clause_text,
        }

    @classmethod
    def analyze_duration_and_termination(cls, text: str) -> Dict[str, Any]:
        """Extract both contract duration and termination clause metadata."""
        duration = cls.extract_duration(text)
        termination = cls.extract_termination_clauses(text)
        return {
            "duration": duration,
            "termination": termination,
        }

