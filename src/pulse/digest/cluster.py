"""News clustering module implementing MVP keyword/entity similarity."""

import re
import uuid
from typing import Any


def _extract_keywords(text: str) -> set[str]:
    """Extract significant words (length > 3, alphanumeric) from text."""
    if not text:
        return set()
    words = re.findall(r"\b[a-zA-Zа-яА-Я0-9]{4,}\b", text.lower())
    # Exclude common stop words
    stop_words = {"сегодня", "вчера", "сообщил", "рассказал", "заявил", "новость", "опубликовал"}
    return {w for w in words if w not in stop_words}


class NewsClusterer:
    """Groups duplicate or related news stories into clusters using heuristic keyword overlap."""

    def __init__(self, similarity_threshold: float = 0.35) -> None:
        self.threshold = similarity_threshold

    def find_or_create_cluster(
        self,
        target_item: dict[str, Any],
        recent_24h_items: list[dict[str, Any]],
    ) -> tuple[str, bool]:
        """Find matching cluster from recent 24h items or create a new cluster ID.

        Args:
            target_item: Dict of item being clustered ('id', 'ru_headline' or 'headline')
            recent_24h_items: List of existing scored/used/archived items from last 24h

        Returns:
            tuple[str, bool]:
                - cluster_id (uuid string)
                - is_archived_cluster (True if cluster was already used in a published issue)
        """
        target_id = str(target_item.get("id", uuid.uuid4()))
        target_headline = target_item.get("ru_headline") or target_item.get("headline", "")
        target_words = _extract_keywords(target_headline)

        if not target_words or not recent_24h_items:
            return target_id, False

        best_cluster_id = None
        best_score = 0.0
        cluster_used = False

        for item in recent_24h_items:
            item_id = str(item.get("id", ""))
            if item_id == target_id:
                continue

            h = item.get("ru_headline") or item.get("headline", "")
            words = _extract_keywords(h)
            if not words:
                continue

            intersection = target_words.intersection(words)
            union = target_words.union(words)
            jaccard = len(intersection) / float(len(union)) if union else 0.0

            if jaccard >= self.threshold and jaccard > best_score:
                best_score = jaccard
                best_cluster_id = item.get("cluster_id") or item_id
                # Check if cluster was already used/archived
                if item.get("status") in ("used", "archived") and item.get("used_in_issue_id"):
                    cluster_used = True

        if best_cluster_id:
            return str(best_cluster_id), cluster_used

        return target_id, False
