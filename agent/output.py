import json
import os
import logging

logging.basicConfig(level=logging.INFO)


class OutputEngine:

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, groups, claims, sources):
        self._generate_digest(groups, sources)
        self._generate_sources_json(claims, sources)

    def _generate_digest(self, groups, sources): # Helps to build digest.md file, for analysis
        source_map = {s.id: s for s in sources}
        file_path = os.path.join(self.output_dir, "digest.md")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Research Digest\n\n")
            f.write(f"**Sources processed:** {len(sources)}  \n")
            f.write(f"**Themes identified:** {len(groups)}  \n\n")
            f.write("---\n\n")

            for group in groups:
                theme = getattr(group, 'theme', 'General') or 'General'
                f.write(f"## Theme: {theme}\n\n")

                for claim in group.claims:
                    source = source_map.get(claim.source_id)
                    source_label = source.title if source else "Unknown"
                    url = source.path_or_url if source else ""
                    confidence = getattr(claim, 'confidence', 'N/A')

                    f.write(f"- **Claim** *(confidence: {confidence})*: {claim.text}\n")
                    f.write(f"  - **Evidence:** \"{claim.evidence}\"\n")
                    f.write(f"  - **Source:** [{source_label}]({url})\n\n")

        logging.info(f"Generated {file_path}")

    def _generate_sources_json(self, claims, sources):
        source_map = {s.id: s for s in sources}

        # Build output keyed by source title (human-readable), Source Json for Understanding
        output = {}
        for source in sources:
            source_claims = [c for c in claims if c.source_id == source.id]
            output[source.title] = {
                "url_or_path": source.path_or_url,
                "source_type": source.source_type,
                "content_length": source.length,
                "claims": [
                    {
                        "claim": c.text,
                        "evidence": c.evidence,
                        "confidence": getattr(c, 'confidence', None),
                    }
                    for c in source_claims
                ]
            }

        file_path = os.path.join(self.output_dir, "sources.json")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            logging.info(f"Generated {file_path}")
        except Exception as e:
            logging.error(f"Failed to write sources.json: {e}")
            # Fallback: write with ascii encoding to avoid any Unicode issues
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=True)
            logging.info(f"Generated {file_path} (ascii fallback)")