import logging
import re
from collections import Counter

logging.basicConfig(level=logging.INFO)


class GroupingEngine:

    def assign_themes(self, groups):
        for group in groups:
            group.theme = self._generate_theme(group)

        return groups

    def _generate_theme(self, group):
        words = []

        for claim in group.claims:
            cleaned = self._clean_text(claim.text)
            words.extend(cleaned.split())

        common = Counter(words).most_common(20)

        theme_words = [
            w for w, _ in common
            if len(w) > 5 and w not in self._stopwords()
        ]

        if not theme_words:
            return "General Insight"

        return " ".join(theme_words[:4]).title()

    def _clean_text(self, text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9 ]+', ' ', text)
        return text

    def _stopwords(self):
        return {
            "the", "is", "are", "was", "were", "has", "have",
            "had", "been", "being", "this", "that", "these",
            "those", "with", "from", "into", "about", "over",
            "under", "between", "among", "vehicle", "vehicles",
            "system", "using", "used", "use", "can", "may",
            "also", "such", "more", "than", "other"
        }