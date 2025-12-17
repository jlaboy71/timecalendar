"""
Help documentation service for providing searchable instructional content.
Comprehensive documentation for the TJM Time Calendar system.

Content is loaded from data/help/ directory with fallback to inline content.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Get the project root directory (3 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
HELP_DATA_DIR = PROJECT_ROOT / "data" / "help"


class HelpService:
    """Service for managing help documentation content."""

    # Role hierarchy for access control
    # employee < manager < admin < superadmin
    ROLE_HIERARCHY = {
        'employee': 0,
        'manager': 1,
        'admin': 2,
        'superadmin': 3
    }

    # Cache for loaded content
    _manifest_cache: Optional[Dict] = None
    _content_cache: Dict[str, str] = {}

    @classmethod
    def _load_manifest(cls) -> Optional[Dict]:
        """Load the manifest.json file containing chapter metadata."""
        if cls._manifest_cache is not None:
            return cls._manifest_cache

        manifest_path = HELP_DATA_DIR / "manifest.json"
        if not manifest_path.exists():
            logger.warning(f"Help manifest not found at {manifest_path}")
            return None

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                cls._manifest_cache = json.load(f)
            return cls._manifest_cache
        except Exception as e:
            logger.error(f"Error loading help manifest: {e}")
            return None

    @classmethod
    def _load_article_content(cls, chapter_id: str, article_id: str) -> Optional[str]:
        """Load article content from markdown file."""
        cache_key = f"{chapter_id}/{article_id}"
        if cache_key in cls._content_cache:
            return cls._content_cache[cache_key]

        article_path = HELP_DATA_DIR / chapter_id / f"{article_id}.md"
        if not article_path.exists():
            logger.warning(f"Help article not found at {article_path}")
            return None

        try:
            with open(article_path, 'r', encoding='utf-8') as f:
                content = f.read()
            cls._content_cache[cache_key] = content
            return content
        except Exception as e:
            logger.error(f"Error loading help article {article_path}: {e}")
            return None

    @classmethod
    def _has_access(cls, user_role: Optional[str], required_role: Optional[str]) -> bool:
        """Check if a user role has access to content requiring a specific role."""
        # If no role required, everyone has access
        if required_role is None:
            return True
        # If user has no role, deny access to restricted content
        if user_role is None:
            return False
        # Check role hierarchy
        user_level = cls.ROLE_HIERARCHY.get(user_role, 0)
        required_level = cls.ROLE_HIERARCHY.get(required_role, 0)
        return user_level >= required_level

    @classmethod
    def get_all_chapters(cls, user_role: Optional[str] = None) -> List[Dict]:
        """Get all chapters with metadata (without full content), filtered by user role."""
        manifest = cls._load_manifest()
        if not manifest:
            return []

        chapters = []
        for chapter_id, chapter in manifest.get("chapters", {}).items():
            # Skip chapters the user doesn't have access to
            if not cls._has_access(user_role, chapter.get("required_role")):
                continue
            chapters.append({
                "id": chapter_id,
                "title": chapter["title"],
                "icon": chapter["icon"],
                "order": chapter["order"],
                "article_count": len(chapter.get("articles", [])),
                "articles": [
                    {"id": a["id"], "title": a["title"]}
                    for a in chapter.get("articles", [])
                ]
            })
        return sorted(chapters, key=lambda x: x["order"])

    @classmethod
    def get_chapter(cls, chapter_id: str, user_role: Optional[str] = None) -> Optional[Dict]:
        """Get a specific chapter with all articles, checking access."""
        manifest = cls._load_manifest()
        if not manifest:
            return None

        chapter = manifest.get("chapters", {}).get(chapter_id)
        if not chapter:
            return None

        # Check if user has access to this chapter
        if not cls._has_access(user_role, chapter.get("required_role")):
            return None

        # Load article content
        articles = []
        for article_meta in chapter.get("articles", []):
            content = cls._load_article_content(chapter_id, article_meta["id"])
            if content:
                articles.append({
                    "id": article_meta["id"],
                    "title": article_meta["title"],
                    "content": content
                })

        return {
            "id": chapter_id,
            "title": chapter["title"],
            "icon": chapter["icon"],
            "articles": articles
        }

    @classmethod
    def get_article(cls, chapter_id: str, article_id: str, user_role: Optional[str] = None) -> Optional[Dict]:
        """Get a specific article, checking access."""
        manifest = cls._load_manifest()
        if not manifest:
            return None

        chapter = manifest.get("chapters", {}).get(chapter_id)
        if not chapter:
            return None

        # Check if user has access to this chapter
        if not cls._has_access(user_role, chapter.get("required_role")):
            return None

        # Find the article metadata
        article_meta = None
        for a in chapter.get("articles", []):
            if a["id"] == article_id:
                article_meta = a
                break

        if not article_meta:
            return None

        # Load content
        content = cls._load_article_content(chapter_id, article_id)
        if not content:
            return None

        return {
            "chapter_id": chapter_id,
            "chapter_title": chapter["title"],
            "id": article_meta["id"],
            "title": article_meta["title"],
            "content": content
        }

    @classmethod
    def search(cls, query: str, user_role: Optional[str] = None) -> List[Dict]:
        """
        Search all help content for matching articles, filtered by user role.

        Args:
            query: Search term
            user_role: User's role for filtering results

        Returns:
            List of matching articles with snippets
        """
        if not query or len(query) < 2:
            return []

        manifest = cls._load_manifest()
        if not manifest:
            return []

        query_lower = query.lower()
        results = []

        for chapter_id, chapter in manifest.get("chapters", {}).items():
            # Skip chapters the user doesn't have access to
            if not cls._has_access(user_role, chapter.get("required_role")):
                continue

            for article_meta in chapter.get("articles", []):
                # Load content for search
                content = cls._load_article_content(chapter_id, article_meta["id"])
                if not content:
                    continue

                # Search in title and content
                title_match = query_lower in article_meta["title"].lower()
                content_match = query_lower in content.lower()

                if title_match or content_match:
                    # Extract snippet around match
                    snippet = ""
                    if content_match:
                        content_lower = content.lower()
                        idx = content_lower.find(query_lower)
                        start = max(0, idx - 50)
                        end = min(len(content), idx + len(query) + 50)
                        snippet = "..." + content[start:end].strip() + "..."

                    results.append({
                        "chapter_id": chapter_id,
                        "chapter_title": chapter["title"],
                        "article_id": article_meta["id"],
                        "article_title": article_meta["title"],
                        "snippet": snippet,
                        "relevance": 2 if title_match else 1
                    })

        # Sort by relevance (title matches first)
        return sorted(results, key=lambda x: -x["relevance"])

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached content. Useful for development/testing."""
        cls._manifest_cache = None
        cls._content_cache = {}
