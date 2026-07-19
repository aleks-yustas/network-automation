from netops_automation.processors.archive import ArchiveProcessor
from netops_automation.processors.postgres_metadata import PostgresMetadataProcessor

PROCESSORS = {
    "archive": ArchiveProcessor,
    "postgres_metadata": PostgresMetadataProcessor,
}

