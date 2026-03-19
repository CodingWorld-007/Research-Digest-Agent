import logging

from agent.ingestion import IngestionEngine
from agent.cleaning import CleaningEngine
from agent.claim_extractor import RuleBasedExtractor
from agent.deduplicator import DeduplicationEngine
from agent.grouper import GroupingEngine
from agent.output import OutputEngine

logging.basicConfig(level=logging.INFO)


class ResearchPipeline:

    def __init__(self):
        self.ingestion = IngestionEngine()
        self.cleaning = CleaningEngine()
        self.extractor = RuleBasedExtractor()
        self.deduplicator = DeduplicationEngine()
        self.grouper = GroupingEngine()
        self.output = OutputEngine()

    def run(self, inputs):
        logging.info("🚀 Starting Research Pipeline")

        # Step 1: Ingestion
        sources = self.ingestion.ingest(inputs)
        logging.info(f"Sources after ingestion: {len(sources)}")

        if not sources:
            logging.warning("No valid sources found. Exiting pipeline.")
            return

        # Step 2: Cleaning
        clean_sources = self.cleaning.clean(sources)
        logging.info(f"Sources after cleaning: {len(clean_sources)}")

        if not clean_sources:
            logging.warning("No valid cleaned content. Exiting pipeline.")
            return

        # Step 3: Claim Extraction
        claims = self.extractor.extract(clean_sources)
        logging.info(f"Total claims extracted: {len(claims)}")

        if not claims:
            logging.warning("No claims extracted. Exiting pipeline.")
            return

        # Step 4: Deduplication
        groups = self.deduplicator.process(claims)
        logging.info(f"Total groups formed: {len(groups)}")

        if not groups:
            logging.warning("No groups formed. Exiting pipeline.")
            return

        # Step 5: Theme Assignment
        themed_groups = self.grouper.assign_themes(groups)

        # Step 6: Output Generation
        self.output.generate(themed_groups, claims, sources)

        logging.info("✅ Pipeline completed successfully")