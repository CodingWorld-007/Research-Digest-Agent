import re
import uuid
import logging
from models.schemas import Claim
from config.settings import USE_LLM, LLM_API_KEY
 
logging.basicConfig(level=logging.INFO)
 
 
class ClaimExtractor:
    def extract(self, sources):
        raise NotImplementedError
 
 
# 🔹 Rule-Based Extractor (Improved)
class RuleBasedExtractor(ClaimExtractor):
 
    MAX_CLAIMS_PER_SOURCE = 40
 
    # Patterns that strongly signal a factual claim
    CLAIM_SIGNALS = [
        r'\d+\s*%',                         # percentages
        r'\$[\d,]+',                         # dollar amounts
        r'\b\d{4}\b',                        # years
        r'\b\d+(\.\d+)?\s*(million|billion|trillion|km|kw|kwh|mph|kg)\b',
        r'\b(first|largest|fastest|most|least|highest|lowest)\b',
        r'\b(study|research|report|data|survey|analysis)\s+(shows?|finds?|suggests?|indicates?|reveals?)\b',
        r'\b(according to|as of|estimated|projected|measured)\b',
    ]
 
    CLAIM_VERBS = [
        "is", "are", "was", "were", "has", "have", "had",
        "shows", "suggests", "indicates", "demonstrates",
        "increases", "reduces", "leads to", "contributes",
        "produces", "generates", "requires", "enables",
        "provides", "offers", "allows", "makes",
        "can", "could", "will", "would",
    ]
 
    REASONING_KEYWORDS = [
        "because", "due to", "as a result", "therefore",
        "consequently", "which means", "leading to", "resulting in",
        "compared to", "relative to", "unlike", "whereas",
    ]
 
    SKIP_PATTERNS = [
        r'^see also', r'^references', r'^external links',
        r'^further reading', r'^notes$', r'^edit$',
    ]
 
    def extract(self, sources):
        all_claims = []
 
        for source in sources:
            sentences = self._split_sentences(source.content)
            claims_for_source = []
 
            for sentence in sentences:
                score = self._score_claim(sentence)
                if score >= 1.5 and self._is_informative(sentence):
                    claim = Claim(
                        id=str(uuid.uuid4()),
                        text=self._normalize_claim(sentence),
                        evidence=sentence.strip(),
                        source_id=source.id,
                        confidence=min(round(score / 4.0, 2), 1.0)  # normalize to 0–1
                    )
                    claims_for_source.append(claim)
 
                if len(claims_for_source) >= self.MAX_CLAIMS_PER_SOURCE:
                    break
 
            logging.info(f"{len(claims_for_source)} claims extracted from: {source.title}")
            all_claims.extend(claims_for_source)
 
        logging.info(f"Total claims extracted: {len(all_claims)}")
        return all_claims
 
    def _split_sentences(self, text):
        return re.split(r'(?<=[.!?]) +', text)
 
    def _score_claim(self, sentence):
        """
        Returns a score (0 = not a claim, >0 = likely claim).
        Higher score = more confident.
        """
        s = sentence.lower().strip()
 
        # Hard filters
        if len(s) < 50 or len(s) > 600:
            return 0
 
        if any(re.match(p, s) for p in self.SKIP_PATTERNS):
            return 0
 
        # Must have at least one verb
        if not any(f' {v} ' in f' {s} ' for v in self.CLAIM_VERBS):
            return 0
 
        score = 0
 
        # Strong signals
        for pattern in self.CLAIM_SIGNALS:
            if re.search(pattern, s, re.IGNORECASE):
                score += 1
 
        # Reasoning / causality adds weight
        if any(k in s for k in self.REASONING_KEYWORDS):
            score += 1
 
        # Comparative / evaluative language
        if re.search(r'\b(more|less|greater|fewer|higher|lower|better|worse)\b', s):
            score += 0.5
 
        return score
 
    def _normalize_claim(self, sentence):
        return sentence.strip()
 
    def _is_informative(self, sentence):
        words = sentence.split()
        unique_words = set(words)

        if len(words) < 8:
            return False

        # low diversity = low information
        if len(unique_words) / len(words) < 0.5:
            return False

        return True
 
# 🔹 LLM Extractor (Placeholder)
class LLMExtractor(ClaimExtractor):
 
    def __init__(self):
        if not LLM_API_KEY:
            raise Exception("LLM API key not provided")
 
    def extract(self, sources):
        raise NotImplementedError("LLM extractor not implemented yet")