class Source:
    def __init__(self, id, title, content, source_type, path_or_url):
        self.id = id
        self.title = title
        self.content = content
        self.source_type = source_type
        self.path_or_url = path_or_url
        self.length = len(content)


class Claim:
    def __init__(self, id, text, evidence, source_id, confidence=0.5):
        self.id = id
        self.text = text
        self.evidence = evidence
        self.source_id = source_id
        self.confidence = confidence  # 0.0 – 1.0


class ClaimGroup:
    def __init__(self, id, claims):
        self.id = id
        self.claims = claims
        self.theme = None

    @property
    def source_ids(self):
        """Unique sources supporting this group."""
        return list({c.source_id for c in self.claims})

    @property
    def avg_confidence(self):
        if not self.claims:
            return 0.0
        return round(sum(c.confidence for c in self.claims) / len(self.claims), 2)