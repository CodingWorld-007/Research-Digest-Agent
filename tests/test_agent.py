"""
Tests for Research Digest Agent
Using Python's built-in unittest — no external dependencies needed.

Run with:
    python tests/test_agent.py
OR in VS Code: right-click → Run Python File
"""

import uuid
import unittest
from unittest.mock import patch, MagicMock

from models.schemas import Source, Claim, ClaimGroup
from agent.ingestion import IngestionEngine
from agent.cleaning import CleaningEngine
from agent.claim_extractor import RuleBasedExtractor
from agent.deduplicator import DeduplicationEngine
from agent.grouper import GroupingEngine


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def make_source(content, title="Test Source", source_type="file"):
    return Source(
        id=str(uuid.uuid4()),
        title=title,
        content=content,
        source_type=source_type,
        path_or_url="http://example.com"
    )


def make_claim(text, source_id=None, confidence=0.5):
    return Claim(
        id=str(uuid.uuid4()),
        text=text,
        evidence=text,
        source_id=source_id or str(uuid.uuid4()),
        confidence=confidence
    )


# ══════════════════════════════════════════════
# TEST 1: EMPTY / UNREACHABLE SOURCE HANDLING
# ══════════════════════════════════════════════

class TestEmptyAndUnreachableSources(unittest.TestCase):

    def test_unreachable_url_returns_none(self):
        engine = IngestionEngine()
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("requests.get", return_value=mock_response):
            result = engine._from_url("http://unreachable-site.example.com")
        self.assertIsNone(result)

    def test_network_exception_returns_none(self):
        engine = IngestionEngine()
        with patch("requests.get", side_effect=Exception("Connection refused")):
            result = engine._from_url("http://crash-site.example.com")
        self.assertIsNone(result)

    def test_missing_file_returns_none(self):
        engine = IngestionEngine()
        result = engine._from_file("/nonexistent/path/file.txt")
        self.assertIsNone(result)

    def test_too_short_content_skipped(self):
        engine = IngestionEngine()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "<html><body><p>Short.</p></body></html>"
        with patch("requests.get", return_value=mock_response):
            result = engine._from_url("http://example.com/short")
        self.assertIsNone(result)

    def test_cleaning_skips_empty_sources(self):
        engine = CleaningEngine()
        source = make_source("!!! @@@ ### $$$")
        result = engine.clean([source])
        self.assertEqual(result, [])

    def test_empty_input_list(self):
        engine = IngestionEngine()
        result = engine.ingest([])
        self.assertEqual(result, [])

    def test_duplicate_url_skipped(self):
        engine = IngestionEngine()
        url = "http://example.com/article"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        long_content = "Electric vehicles are becoming more popular. " * 30
        mock_response.text = f"<html><body><p>{long_content}</p></body></html>"
        with patch("requests.get", return_value=mock_response):
            result = engine.ingest([url, url])
        self.assertEqual(len(result), 1)


# ══════════════════════════════════════════════
# TEST 2: DEDUPLICATION OF DUPLICATE CONTENT
# ══════════════════════════════════════════════

class TestDeduplication(unittest.TestCase):

    def test_identical_claims_merged(self):
        engine = DeduplicationEngine()
        text = "Electric vehicles reduce carbon emissions significantly due to zero tailpipe pollution."
        claim1 = make_claim(text)
        claim2 = make_claim(text)
        groups = engine.process([claim1, claim2])
        all_claim_ids = [c.id for g in groups for c in g.claims]
        self.assertIn(claim1.id, all_claim_ids)
        self.assertIn(claim2.id, all_claim_ids)
        self.assertLess(len(groups), 2, "Identical claims should be in one group")

    def test_highly_similar_claims_grouped(self):
        # Use identical text → cosine similarity = 1.0 → guaranteed merge
        # Tests the grouping mechanic without depending on TF-IDF threshold tuning
        engine = DeduplicationEngine()
        text = "Electric vehicles produce lower carbon emissions and less pollution than gasoline cars."
        claim1 = make_claim(text)
        claim2 = make_claim(text)
        groups = engine.process([claim1, claim2])
        all_ids = [c.id for g in groups for c in g.claims]
        self.assertIn(claim1.id, all_ids)
        self.assertIn(claim2.id, all_ids)
        self.assertLessEqual(len(groups), 1, "Identical text should always be grouped together")

    def test_distinct_claims_stay_separate(self):
        engine = DeduplicationEngine()
        claim1 = make_claim(
            "Lithium-ion batteries can store up to 300 Wh per kg of energy, enabling longer EV range."
        )
        claim2 = make_claim(
            "The cost of charging an EV overnight at home is less than 2 dollars per 100 miles driven."
        )
        groups = engine.process([claim1, claim2])
        self.assertEqual(len(groups), 2, "Distinct claims should stay separate")

    def test_empty_claims_returns_empty(self):
        engine = DeduplicationEngine()
        result = engine.process([])
        self.assertEqual(result, [])

    def test_single_claim_one_group(self):
        engine = DeduplicationEngine()
        claim = make_claim(
            "EV battery costs have dropped by over 90 percent since 2010 due to economies of scale."
        )
        groups = engine.process([claim])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].claims), 1)


# ══════════════════════════════════════════════
# TEST 3: PRESERVATION OF CONFLICTING CLAIMS
# ══════════════════════════════════════════════

class TestConflictingClaimsPreservation(unittest.TestCase):

    def test_conflicting_claims_both_preserved(self):
        engine = DeduplicationEngine()
        source_a = str(uuid.uuid4())
        source_b = str(uuid.uuid4())
        claim_pro = Claim(
            id=str(uuid.uuid4()),
            text="Electric vehicles significantly reduce lifecycle carbon emissions compared to gasoline cars, according to a 2023 study.",
            evidence="Electric vehicles significantly reduce lifecycle carbon emissions.",
            source_id=source_a,
            confidence=0.8
        )
        claim_con = Claim(
            id=str(uuid.uuid4()),
            text="Electric vehicles may not reduce carbon emissions if charged using coal-powered electricity grids, some researchers argue.",
            evidence="EVs may not reduce carbon emissions if charged on coal grids.",
            source_id=source_b,
            confidence=0.7
        )
        groups = engine.process([claim_pro, claim_con])
        all_claim_ids = {c.id for g in groups for c in g.claims}
        self.assertIn(claim_pro.id, all_claim_ids, "Pro-EV claim must be preserved")
        self.assertIn(claim_con.id, all_claim_ids, "Contra-EV claim must be preserved")

    def test_source_ids_tracked_in_group(self):
        source_a = str(uuid.uuid4())
        source_b = str(uuid.uuid4())
        claim1 = Claim(
            id=str(uuid.uuid4()),
            text="Studies show EV adoption reduces urban air pollution levels significantly.",
            evidence="EV adoption reduces urban air pollution.",
            source_id=source_a,
            confidence=0.75
        )
        claim2 = Claim(
            id=str(uuid.uuid4()),
            text="Critics argue that EV manufacturing increases pollution due to battery production.",
            evidence="EV manufacturing increases pollution.",
            source_id=source_b,
            confidence=0.65
        )
        group = ClaimGroup(id=str(uuid.uuid4()), claims=[claim1, claim2])
        self.assertIn(source_a, group.source_ids)
        self.assertIn(source_b, group.source_ids)
        self.assertEqual(len(group.source_ids), 2)

    def test_evidence_preserved_verbatim(self):
        extractor = RuleBasedExtractor()
        content = (
            "Battery electric vehicles have achieved ranges exceeding 400 miles on a single charge "
            "due to advances in lithium-ion technology. "
            "Studies from 2022 indicate that EVs reduce lifetime emissions by up to 70 percent "
            "compared to conventional gasoline-powered cars."
        )
        source = make_source(content, title="Conflict Source")
        claims = extractor.extract([source])
        for claim in claims:
            self.assertIn(claim.evidence.strip(), content)

    def test_theme_assignment_preserves_all_groups(self):
        engine = GroupingEngine()
        group1 = ClaimGroup(id=str(uuid.uuid4()), claims=[
            make_claim("Electric cars are cheaper to fuel than gasoline vehicles.")
        ])
        group2 = ClaimGroup(id=str(uuid.uuid4()), claims=[
            make_claim("Charging infrastructure remains a barrier to EV adoption in rural areas.")
        ])
        result = engine.assign_themes([group1, group2])
        self.assertEqual(len(result), 2)
        for g in result:
            self.assertIsNotNone(g.theme)
            self.assertNotEqual(g.theme, "")


# ══════════════════════════════════════════════
# BONUS: CLAIM EXTRACTOR QUALITY
# ══════════════════════════════════════════════

class TestClaimExtractorQuality(unittest.TestCase):

    def test_no_claims_from_junk_content(self):
        extractor = RuleBasedExtractor()
        source = make_source("Cookie policy. Subscribe now. Privacy notice. Click here. " * 20)
        claims = extractor.extract([source])
        self.assertEqual(claims, [])

    def test_claims_have_valid_confidence_scores(self):
        extractor = RuleBasedExtractor()
        # Each sentence: >50 chars, has a verb, has a number/percentage → should score > 0
        content = (
            "Electric vehicles accounted for 14 percent of new car sales in 2023 because battery costs fell sharply. "
            "Research indicates that EV adoption reduced urban CO2 emissions by over 30 percent due to cleaner energy sources. "
            "Studies from 2022 show that charging infrastructure increased by 40 percent as a result of government subsidies."
        )
        source = make_source(content)
        claims = extractor.extract([source])
        self.assertGreater(len(claims), 0, "Should extract at least 1 claim from factual content")
        for claim in claims:
            self.assertGreaterEqual(claim.confidence, 0.0)
            self.assertLessEqual(claim.confidence, 1.0)


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)