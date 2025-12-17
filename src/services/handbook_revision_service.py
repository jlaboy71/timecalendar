"""
Handbook revision service for managing handbook updates with AI diff detection.
"""
import os
import json
import logging
import difflib
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from src.models.handbook_revision import HandbookRevision

logger = logging.getLogger(__name__)


class HandbookRevisionService:
    """Service for managing handbook revisions with AI-powered diff analysis."""

    def __init__(self, db: Session):
        self.db = db

    def get_active_revision(self) -> Optional[HandbookRevision]:
        """Get the currently active handbook revision."""
        stmt = select(HandbookRevision).where(HandbookRevision.is_active == True)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_revision(self) -> Optional[HandbookRevision]:
        """Get the most recent revision regardless of active status."""
        stmt = select(HandbookRevision).order_by(HandbookRevision.created_at.desc())
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_revisions(self) -> List[HandbookRevision]:
        """Get all revisions ordered by version descending."""
        stmt = select(HandbookRevision).order_by(HandbookRevision.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_revision_by_id(self, revision_id: int) -> Optional[HandbookRevision]:
        """Get a specific revision by ID."""
        stmt = select(HandbookRevision).where(HandbookRevision.id == revision_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_revision(
        self,
        content: str,
        created_by: int,
        version: Optional[str] = None,
        activate: bool = True
    ) -> Tuple[HandbookRevision, Dict]:
        """
        Create a new handbook revision.

        Args:
            content: New handbook content (markdown)
            created_by: User ID of the person making changes
            version: Optional version number (auto-incremented if not provided)
            activate: Whether to make this the active version

        Returns:
            Tuple of (new revision, change report)
        """
        # Get current active revision for comparison
        current = self.get_active_revision()

        # Calculate version number
        if not version:
            if current:
                # Increment version
                try:
                    major, minor = current.version.split('.')
                    version = f"{major}.{int(minor) + 1}"
                except:
                    version = "1.1"
            else:
                version = "1.0"

        # Calculate differences
        change_report = self._analyze_changes(
            current.content if current else "",
            content
        )

        # Get AI summary of changes if significant changes found
        ai_summary = None
        if change_report['has_changes'] and len(change_report['changes']) > 0:
            ai_summary = self._generate_ai_summary(change_report)

        # Deactivate current version if activating new one
        if activate and current:
            current.is_active = False

        # Create new revision
        revision = HandbookRevision(
            version=version,
            content=content,
            change_summary=ai_summary,
            change_details=json.dumps(change_report['changes']),
            created_by=created_by,
            is_active=activate
        )

        self.db.add(revision)
        self.db.commit()
        self.db.refresh(revision)

        logger.info(f"Created handbook revision {version} by user {created_by}")

        return revision, change_report

    def _analyze_changes(self, old_content: str, new_content: str) -> Dict:
        """
        Analyze differences between old and new content.

        Returns:
            Dictionary with change details
        """
        if not old_content:
            return {
                'has_changes': True,
                'is_new': True,
                'changes': [{'type': 'new', 'description': 'Initial handbook content'}],
                'stats': {'additions': len(new_content.split('\n')), 'deletions': 0}
            }

        # Split into lines for comparison
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        # Calculate diff
        differ = difflib.unified_diff(old_lines, new_lines, lineterm='')
        diff_lines = list(differ)

        # Parse changes
        changes = []
        additions = 0
        deletions = 0
        current_section = None

        for line in diff_lines:
            if line.startswith('@@'):
                continue
            elif line.startswith('---') or line.startswith('+++'):
                continue
            elif line.startswith('+') and not line.startswith('+++'):
                additions += 1
                # Check if it's a section header
                clean_line = line[1:].strip()
                if clean_line.startswith('#'):
                    current_section = clean_line.lstrip('#').strip()
                    changes.append({
                        'type': 'added_section',
                        'section': current_section,
                        'description': f"Added section: {current_section}"
                    })
                elif len(clean_line) > 10:  # Meaningful content
                    changes.append({
                        'type': 'addition',
                        'section': current_section,
                        'preview': clean_line[:100]
                    })
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
                clean_line = line[1:].strip()
                if clean_line.startswith('#'):
                    current_section = clean_line.lstrip('#').strip()
                    changes.append({
                        'type': 'removed_section',
                        'section': current_section,
                        'description': f"Removed section: {current_section}"
                    })
                elif len(clean_line) > 10:
                    changes.append({
                        'type': 'deletion',
                        'section': current_section,
                        'preview': clean_line[:100]
                    })

        # Consolidate similar changes
        consolidated = self._consolidate_changes(changes)

        return {
            'has_changes': additions > 0 or deletions > 0,
            'is_new': False,
            'changes': consolidated,
            'stats': {
                'additions': additions,
                'deletions': deletions,
                'total_lines_changed': additions + deletions
            }
        }

    def _consolidate_changes(self, changes: List[Dict]) -> List[Dict]:
        """Consolidate multiple small changes into meaningful summaries."""
        if len(changes) == 0:
            return []

        # Group by section
        sections = {}
        for change in changes:
            section = change.get('section', 'General')
            if section not in sections:
                sections[section] = {'additions': 0, 'deletions': 0, 'items': []}

            if change['type'] in ['addition', 'added_section']:
                sections[section]['additions'] += 1
            elif change['type'] in ['deletion', 'removed_section']:
                sections[section]['deletions'] += 1

            sections[section]['items'].append(change)

        # Create consolidated list
        result = []
        for section, data in sections.items():
            if data['additions'] > 0 or data['deletions'] > 0:
                summary = []
                if data['additions'] > 0:
                    summary.append(f"+{data['additions']} additions")
                if data['deletions'] > 0:
                    summary.append(f"-{data['deletions']} deletions")

                result.append({
                    'section': section,
                    'summary': ', '.join(summary),
                    'details': data['items'][:3]  # Keep first 3 for detail
                })

        return result

    def _generate_ai_summary(self, change_report: Dict) -> str:
        """
        Generate an AI summary of changes using Anthropic API.

        Falls back to basic summary if API not available.
        """
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                return self._generate_basic_summary(change_report)

            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)

            # Build prompt from changes
            changes_text = []
            for change in change_report.get('changes', []):
                section = change.get('section', 'General')
                summary = change.get('summary', '')
                changes_text.append(f"- {section}: {summary}")

            stats = change_report.get('stats', {})

            prompt = f"""Summarize the following changes to an employee handbook in 2-3 sentences.
Focus on what policies were updated and any important implications for employees.

Changes made:
{chr(10).join(changes_text)}

Statistics: {stats.get('additions', 0)} additions, {stats.get('deletions', 0)} deletions

Write a concise, professional summary suitable for an HR announcement."""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"AI summary generation failed: {str(e)}")
            return self._generate_basic_summary(change_report)

    def _generate_basic_summary(self, change_report: Dict) -> str:
        """Generate a basic summary without AI."""
        stats = change_report.get('stats', {})
        changes = change_report.get('changes', [])

        if change_report.get('is_new'):
            return "Initial handbook version created."

        sections_affected = list(set(c.get('section', 'General') for c in changes if c.get('section')))

        parts = []
        if stats.get('additions', 0) > 0:
            parts.append(f"{stats['additions']} lines added")
        if stats.get('deletions', 0) > 0:
            parts.append(f"{stats['deletions']} lines removed")

        summary = f"Handbook updated: {', '.join(parts)}."

        if sections_affected:
            summary += f" Sections affected: {', '.join(sections_affected[:3])}"
            if len(sections_affected) > 3:
                summary += f" and {len(sections_affected) - 3} more"
            summary += "."

        return summary

    def activate_revision(self, revision_id: int) -> bool:
        """
        Activate a specific revision (make it the current version).

        Args:
            revision_id: ID of revision to activate

        Returns:
            True if successful
        """
        revision = self.get_revision_by_id(revision_id)
        if not revision:
            return False

        # Deactivate all others
        stmt = update(HandbookRevision).where(
            HandbookRevision.id != revision_id
        ).values(is_active=False)
        self.db.execute(stmt)

        # Activate this one
        revision.is_active = True
        self.db.commit()

        logger.info(f"Activated handbook revision {revision.version}")
        return True

    def generate_change_report(self, revision_id: int) -> Dict:
        """
        Generate a downloadable change report for a revision.

        Args:
            revision_id: ID of revision to report on

        Returns:
            Dictionary with report data
        """
        revision = self.get_revision_by_id(revision_id)
        if not revision:
            return {'error': 'Revision not found'}

        # Get previous revision for comparison
        stmt = select(HandbookRevision).where(
            HandbookRevision.created_at < revision.created_at
        ).order_by(HandbookRevision.created_at.desc())
        previous = self.db.execute(stmt).scalar_one_or_none()

        report = {
            'version': revision.version,
            'created_at': revision.created_at.isoformat(),
            'created_by': revision.author.username if revision.author else 'Unknown',
            'summary': revision.change_summary,
            'changes': json.loads(revision.change_details) if revision.change_details else [],
            'previous_version': previous.version if previous else None
        }

        return report
