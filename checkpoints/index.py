import logging
import hashlib

from typing import Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class StateManager:
    def __init__(self):
        self.seen_urls = set()
        self.entity_database: Dict[str, dict] = {}
        self.logger = logging.getLogger("StateManager")

    def generate_key(self, identifier: str) -> str:
        return hashlib.sha256(identifier.lower().strip().encode('utf-8')).hexdigest()

    def upsert_entity(self, entity: dict):
        primary_key = self.generate_key(entity['unique_identifier'])
        
        if primary_key in self.entity_database:
            self.logger.info(f"Entity exists. Updating record: {entity['unique_identifier']}")
            existing = self.entity_database[primary_key]
            existing.setdefault('metrics', {}).update(entity.get('metrics', {}))
            
            if entity['sentiment_analysis']!= existing['sentiment_analysis']:
                 existing['sentiment_analysis'] += f" | UPDATE: {entity['sentiment_analysis']}"
        else:
            self.logger.info(f"New entity discovered. Inserting record: {entity['unique_identifier']}")
            self.entity_database[primary_key] = entity

    def log_url_traversal(self, url: str):
        self.seen_urls.add(url)

    def is_url_seen(self, url: str) -> bool:
        return url in self.seen_urls

global_state = StateManager()