import re
import logging
from models.schemas import Source

logging.basicConfig(level=logging.INFO)


class CleaningEngine:

    def clean(self, sources):
        cleaned_sources = []

        for source in sources:
            try:
                cleaned_text = self._clean_text(source.content)

                if not cleaned_text:
                    logging.warning(f"Empty after cleaning: {source.title}")
                    continue

                source.content = cleaned_text
                source.length = len(cleaned_text)

                cleaned_sources.append(source)

            except Exception as e:
                logging.error(f"Cleaning failed for {source.title}: {e}")

        logging.info(f"Total cleaned sources: {len(cleaned_sources)}")
        return cleaned_sources

    def _clean_text(self, text):
        text = self._normalize_whitespace(text)
        text = self._remove_noise(text)
        sentences = self._split_sentences(text)
        sentences = self._filter_sentences(sentences)

        return " ".join(sentences)

    def _normalize_whitespace(self, text):
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _remove_noise(self, text):
        # remove non-ascii
        text = re.sub(r"[^\x00-\x7F]+", " ", text)

        text = re.sub(r'(?<!\d)(\b\d{1,3}\b\s+){2,4}(?=[A-Z])', '', text)

        # remove inline citations like [13]
        text = re.sub(r'\[\d+\]', '', text)

        # remove weird symbols
        text = re.sub(r"[^a-zA-Z0-9.,;:%()\- ]+", " ", text)

        return text

    def _split_sentences(self, text):
        # simple sentence split (upgrade later if needed)
        sentences = re.split(r'(?<=[.!?]) +', text)
        return sentences

    def _filter_sentences(self, sentences):
        filtered = []

        for s in sentences:
            s = s.strip()

            # skip very short sentences
            if len(s) < 40:
                continue

            # skip likely junk lines
            if any(keyword in s.lower() for keyword in ["cookie", "privacy policy", "subscribe"]):
                continue

            filtered.append(s)

        return filtered