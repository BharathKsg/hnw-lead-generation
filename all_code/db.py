"""
lib/db.py
─────────
MongoDB storage layer for HNW leads.

- Upserts on (full_name, city) to avoid duplicates.
- Keeps the highest overall_hni_score when the same person is seen again.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

from config.settings import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION

logger = logging.getLogger(__name__)


class LeadStore:
    def __init__(self):
        self.client     = MongoClient(MONGO_URI)
        self.db         = self.client[MONGO_DB_NAME]
        self.collection = self.db[MONGO_COLLECTION]
        self._ensure_indexes()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _ensure_indexes(self):
        self.collection.create_index(
            [("full_name", 1), ("city", 1)],
            unique=True,
            name="unique_lead",
        )
        self.collection.create_index("overall_hni_score", name="hni_score_idx")
        self.collection.create_index("qualification_status", name="status_idx")
        logger.debug("[DB] indexes ensured")

    # ── Write ─────────────────────────────────────────────────────────────────

    def upsert_leads(self, leads: List[Dict[str, Any]]) -> int:
        """
        Upsert a list of lead dicts.
        Returns the number of documents inserted or modified.
        """
        if not leads:
            return 0

        ops = []
        now = datetime.now(timezone.utc).isoformat()

        for lead in leads:
            name = lead.get("full_name")
            city = lead.get("city", "")
            if not name:
                continue

            lead["updated_at"] = now
            ops.append(
                UpdateOne(
                    {"full_name": name, "city": city},
                    {
                        "$setOnInsert": {"created_at": now},
                        "$set": lead,
                    },
                    upsert=True,
                )
            )

        if not ops:
            return 0

        try:
            result = self.collection.bulk_write(ops, ordered=False)
            affected = result.upserted_count + result.modified_count
            logger.info(f"[DB] upserted={result.upserted_count} modified={result.modified_count}")
            return affected
        except BulkWriteError as bwe:
            logger.warning(f"[DB] bulk write partial error: {bwe.details}")
            return 0

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_leads(
        self,
        min_score: int = 0,
        status: str = None,
        city: str = None,
        limit: int = 500,
    ) -> List[Dict]:
        query: Dict[str, Any] = {}
        if min_score:
            query["overall_hni_score"] = {"$gte": min_score}
        if status:
            query["qualification_status"] = status
        if city:
            query["city"] = {"$regex": city, "$options": "i"}

        cursor = (
            self.collection.find(query, {"_id": 0})
            .sort("overall_hni_score", -1)
            .limit(limit)
        )
        return list(cursor)

    def close(self):
        self.client.close()
