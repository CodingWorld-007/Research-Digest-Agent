import os
import uuid
import requests
from bs4 import BeautifulSoup
import logging

from models.schemas import Source
from config.settings import MIN_CONTENT_LENGTH, MAX_CONTENT_LENGTH

logging.basicConfig(level=logging.INFO)


class IngestionEngine:

    def __init__(self):
        self.seen_sources = set()

    def ingest(self, inputs):
        sources = []

        for item in inputs:
            if item.startswith("http"):
                src = self._from_url(item)
            else:
                src = self._from_file(item)

            if src:
                sources.append(src)

        logging.info(f"Total sources ingested: {len(sources)}")
        return sources

    def _from_url(self, url):
        if url in self.seen_sources:
            logging.warning(f"Duplicate URL skipped: {url}")
            return None

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                logging.error(f"Failed to fetch: {url}")
                return None

            if "text/html" not in response.headers.get("Content-Type", ""):
                logging.warning(f"Non-HTML content skipped: {url}")
                return None

            content = response.text

            if len(content) > MAX_CONTENT_LENGTH:
                logging.warning(f"Content too large, truncating: {url}")
                content = content[:MAX_CONTENT_LENGTH]

            soup = BeautifulSoup(response.text, "html.parser")

            paragraphs = [p.get_text() for p in soup.find_all("p")]
            content = " ".join(paragraphs).strip()

            if len(content) < MIN_CONTENT_LENGTH:
                logging.warning(f"Content too short: {url}")
                return None

            title = soup.title.string if soup.title else "Untitled"

            source = Source(
                id=str(uuid.uuid4()),
                title=title,
                content=content,
                source_type="url",
                path_or_url=url
            )

            self.seen_sources.add(url)
            return source

        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            return None

    def _from_file(self, path):
        if not os.path.exists(path):
            logging.error(f"File not found: {path}")
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            if len(content) > MAX_CONTENT_LENGTH:
                logging.warning(f"File too large, truncating: {path}")
                content = content[:MAX_CONTENT_LENGTH]

            if len(content) < MIN_CONTENT_LENGTH:
                logging.warning(f"File too short: {path}")
                return None

            return Source(
                id=str(uuid.uuid4()),
                title=os.path.basename(path),
                content=content,
                source_type="file",
                path_or_url=path
            )

        except Exception as e:
            logging.error(f"Error reading file {path}: {e}")
            return None