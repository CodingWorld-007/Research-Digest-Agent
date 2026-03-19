import uuid
import logging
import re
from models.schemas import ClaimGroup
from config.settings import SIMILARITY_THRESHOLD

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO)


class DeduplicationEngine:

    def process(self, claims):
        if not claims:
            logging.warning("No claims to process")
            return []

        topic_buckets = {}

        for claim in claims:
            topic = self._assign_topic(claim.text)
            topic_buckets.setdefault(topic, []).append(claim)

        all_groups = []

        for topic, topic_claims in topic_buckets.items():
            if not topic_claims:
                continue

            texts = [
                self._normalize_semantics(
                    self._simplify_text(
                        self._normalize_text(c.text)
                    )
                )
                for c in topic_claims
            ]

            # Vectorize
            vectorizer = TfidfVectorizer(stop_words='english')
            vectors = vectorizer.fit_transform(texts)

            similarity_matrix = cosine_similarity(vectors)

            visited = set()

            # 🔹 Step 3: Grouping inside topic
            for i in range(len(topic_claims)):
                if i in visited:
                    continue

                group_claims = [topic_claims[i]]
                visited.add(i)

                for j in range(i + 1, len(topic_claims)):
                    if j in visited:
                        continue

                    sim_score = similarity_matrix[i][j]
                    overlap_score = self._keyword_overlap(texts[i], texts[j])

                    if sim_score >= SIMILARITY_THRESHOLD or overlap_score > 0.3:
                        group_claims.append(topic_claims[j])
                        visited.add(j)

                group = ClaimGroup(
                    id=str(uuid.uuid4()),
                    claims=group_claims
                )

                all_groups.append(group)

        logging.info(f"Reduced {len(claims)} → {len(all_groups)} groups")
        return all_groups

    def _normalize_text(self, text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9 ]+', ' ', text)
        return text

    def _simplify_text(self, text):
        text = text.lower()

        # remove numbers
        text = re.sub(r'\d+', '', text)

        # remove punctuation
        text = re.sub(r'[^a-z0-9 ]+', ' ', text)

        words = text.split()

        # stronger stopwords
        stopwords = {
            "the", "is", "are", "was", "were", "has", "have", "had",
            "been", "being", "in", "on", "at", "by", "for", "with",
            "about", "into", "through", "during", "of", "to", "and",
            "a", "an", "this", "that", "these", "those", "their",
            "there", "which", "such", "other"
        }

        important = [
            w for w in words
            if w not in stopwords and len(w) > 3
        ]

        return " ".join(important)

    def _keyword_overlap(self, text1, text2):
        set1 = set(text1.split())
        set2 = set(text2.split())

        if not set1 or not set2:
            return 0

        overlap = len(set1 & set2) / max(len(set1), 1)
        return overlap
    
    def _generalize_text(self, text):
        text = text.lower()

        # remove numbers (very important)
        text = re.sub(r'\d+', '', text)

        # remove years like 2023, 2022
        text = re.sub(r'\b(19|20)\d{2}\b', '', text)

        # remove extra spaces
        text = re.sub(r'\s+', ' ', text)

        return text.strip()
    
    def _normalize_semantics(self, text):
        replacements = {
            "efficiency": "efficient",
            "efficient": "efficient",
            "efficiencies": "efficient",

            "emissions": "emission",
            "pollution": "emission",

            "vehicles": "vehicle",
            "cars": "vehicle",

            "batteries": "battery",

            "increase": "growth",
            "increased": "growth",
            "growth": "growth",

            "reduce": "reduction",
            "reduced": "reduction"
        }

        words = text.split()
        normalized = [replacements.get(w, w) for w in words]

        return " ".join(normalized)

    def _assign_topic(self, text):
        text = text.lower()

        if any(k in text for k in ["law", "regulation", "policy", "legislation", "govern", "legal", "act", "bill"]):
            return "regulation"

        if any(k in text for k in ["bias", "fairness", "discriminat", "race", "gender", "equity"]):
            return "bias"

        if any(k in text for k in ["safety", "risk", "existential", "alignment", "catastrophe", "threat"]):
            return "safety"

        if any(k in text for k in ["agi", "general intelligence", "superintelligence", "human-level"]):
            return "agi"

        if any(k in text for k in ["ethic", "moral", "responsible", "transparent", "accountab"]):
            return "ethics"

        if any(k in text for k in ["survey", "study", "research", "report", "found", "according"]):
            return "research"

        return "general"