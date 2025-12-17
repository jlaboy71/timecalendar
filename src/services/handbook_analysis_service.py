"""
Handbook Analysis Service using Claude API.

Extracts policy values from uploaded handbook documents,
detects changes from current policies, and generates
friendly summaries for employee communication.
"""
import hashlib
import os
import json
from datetime import datetime, date
from typing import Optional, Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select
import anthropic

from src.models.handbook_upload import HandbookUpload
from src.models.policy_change_log import PolicyChangeLog
from src.models.leave_policy import LeavePolicy
from src.models.leave_type import LeaveType
from src.models.user import User


# Policy type definitions for extraction
POLICY_TYPES = {
    'sick_carryover_max': {
        'name': 'Sick Time Carryover Maximum',
        'unit': 'hours',
        'keywords': ['sick', 'carryover', 'rollover', 'maximum', 'cap', 'limit']
    },
    'sick_accrual_rate': {
        'name': 'Sick Time Accrual Rate',
        'unit': 'hours',
        'keywords': ['sick', 'accrual', 'earn', 'accumulate']
    },
    'vacation_days': {
        'name': 'Vacation Days',
        'unit': 'days',
        'keywords': ['vacation', 'annual', 'PTO', 'paid time off']
    },
    'vacation_carryover_max': {
        'name': 'Vacation Carryover Maximum',
        'unit': 'hours',
        'keywords': ['vacation', 'carryover', 'rollover', 'maximum']
    },
    'personal_days': {
        'name': 'Personal Days',
        'unit': 'days',
        'keywords': ['personal', 'floating', 'discretionary']
    },
    'wfh_weekly_limit': {
        'name': 'Work From Home Weekly Limit',
        'unit': 'days',
        'keywords': ['remote', 'work from home', 'WFH', 'telework', 'weekly']
    },
    'bereavement_days': {
        'name': 'Bereavement Leave',
        'unit': 'days',
        'keywords': ['bereavement', 'funeral', 'death', 'family loss']
    },
    'max_annual_sick_hours': {
        'name': 'Maximum Annual Sick Hours',
        'unit': 'hours',
        'keywords': ['sick', 'annual', 'maximum', 'yearly', 'cap']
    }
}


class HandbookAnalysisService:
    """
    Service for analyzing handbook documents using Claude API.

    Extracts policy values, detects changes, and generates
    employee-friendly summaries of policy updates.
    """

    def __init__(self, db: Session, api_key: Optional[str] = None):
        """
        Initialize the service.

        Args:
            db: Database session
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.db = db
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file for duplicate detection.

        Args:
            file_path: Path to the file

        Returns:
            Hex string of file hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def check_for_duplicate(self, file_hash: str) -> Optional[HandbookUpload]:
        """
        Check if file hash matches a previous upload.

        Args:
            file_hash: SHA-256 hash of uploaded file

        Returns:
            Matching HandbookUpload if found
        """
        stmt = select(HandbookUpload).where(HandbookUpload.file_hash == file_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_next_version(self) -> str:
        """
        Generate the next version number.

        Returns:
            Version string (e.g., "v1.0", "v2.0")
        """
        stmt = select(HandbookUpload).order_by(HandbookUpload.id.desc())
        latest = self.db.execute(stmt).scalar_one_or_none()

        if not latest:
            return "v1.0"

        # Parse existing version
        try:
            current = latest.version.replace('v', '')
            major = int(float(current))
            return f"v{major + 1}.0"
        except (ValueError, AttributeError):
            return f"v{(latest.id or 0) + 1}.0"

    async def analyze_handbook_content(self, content: str) -> Dict[str, Any]:
        """
        Use Claude to analyze handbook content and extract policy values.

        Args:
            content: Text content of the handbook

        Returns:
            Dictionary with extracted policies and analysis
        """
        if not self.client:
            return {
                'error': 'Claude API not configured. Set ANTHROPIC_API_KEY environment variable.',
                'policies': {},
                'raw_response': None
            }

        extraction_prompt = """You are analyzing an employee handbook to extract policy values.
Extract the following policy types and their values:

1. Sick Time Carryover Maximum (by state/city if specified)
2. Sick Time Accrual Rate
3. Maximum Annual Sick Hours
4. Vacation Days by Tenure Tier
5. Vacation Carryover Maximum
6. Personal Days Allocation
7. WFH/Remote Work Weekly Limits
8. Bereavement Leave Days

For each policy found, provide:
- policy_type: one of (sick_carryover_max, sick_accrual_rate, max_annual_sick_hours, vacation_days, vacation_carryover_max, personal_days, wfh_weekly_limit, bereavement_days)
- value: numeric value
- unit: "hours" or "days"
- location_state: state code if location-specific (e.g., "IL"), or null for default
- location_city: city name if city-specific, or null
- relevant_text: the exact text excerpt from the handbook

Return your response as a JSON object with this structure:
{
  "policies": [
    {
      "policy_type": "sick_carryover_max",
      "value": 80,
      "unit": "hours",
      "location_state": "IL",
      "location_city": null,
      "relevant_text": "Illinois employees may carry over up to 80 hours..."
    }
  ],
  "summary": "Brief summary of the handbook's leave policies"
}

IMPORTANT: Only include policies you can find explicit values for. Do not guess or infer values.
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": f"{extraction_prompt}\n\nHandbook Content:\n{content[:50000]}"  # Limit content size
                    }
                ]
            )

            # Parse the response
            response_text = response.content[0].text

            # Try to extract JSON from response
            try:
                # Look for JSON in the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    result = json.loads(json_match.group())
                    return {
                        'policies': result.get('policies', []),
                        'summary': result.get('summary', ''),
                        'raw_response': response_text
                    }
            except json.JSONDecodeError:
                pass

            return {
                'policies': [],
                'summary': response_text,
                'raw_response': response_text,
                'error': 'Could not parse structured response'
            }

        except Exception as e:
            return {
                'error': str(e),
                'policies': [],
                'raw_response': None
            }

    def get_current_policy_values(self) -> Dict[str, Dict]:
        """
        Get current policy values from database for comparison.

        Returns:
            Dictionary mapping policy_type to current values
        """
        current_values = {}

        # Get all active leave policies
        today = date.today()
        stmt = select(LeavePolicy).where(
            LeavePolicy.effective_date <= today,
            (LeavePolicy.end_date.is_(None) | (LeavePolicy.end_date >= today))
        )
        policies = self.db.execute(stmt).scalars().all()

        for policy in policies:
            stmt = select(LeaveType).where(LeaveType.id == policy.leave_type_id)
            leave_type = self.db.execute(stmt).scalar_one_or_none()
            if not leave_type:
                continue

            location_key = (policy.location_state, policy.location_city)

            # Map leave type to policy types
            if leave_type.code == 'SICK':
                if policy.max_carryover_hours:
                    key = f"sick_carryover_max:{location_key}"
                    current_values[key] = {
                        'value': float(policy.max_carryover_hours),
                        'unit': 'hours',
                        'location_state': policy.location_state,
                        'location_city': policy.location_city,
                        'policy_id': policy.id
                    }
                if policy.max_annual_hours:
                    key = f"max_annual_sick_hours:{location_key}"
                    current_values[key] = {
                        'value': float(policy.max_annual_hours),
                        'unit': 'hours',
                        'location_state': policy.location_state,
                        'location_city': policy.location_city,
                        'policy_id': policy.id
                    }

            elif leave_type.code == 'VACATION':
                if policy.max_carryover_hours:
                    key = f"vacation_carryover_max:{location_key}"
                    current_values[key] = {
                        'value': float(policy.max_carryover_hours),
                        'unit': 'hours',
                        'location_state': policy.location_state,
                        'location_city': policy.location_city,
                        'policy_id': policy.id
                    }

        return current_values

    def compare_policies(
        self,
        extracted: List[Dict],
        current: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Compare extracted policies to current values.

        Args:
            extracted: List of extracted policies from handbook
            current: Dictionary of current policy values

        Returns:
            List of detected changes
        """
        changes = []

        for policy in extracted:
            policy_type = policy.get('policy_type')
            location_key = (policy.get('location_state'), policy.get('location_city'))
            lookup_key = f"{policy_type}:{location_key}"

            new_value = policy.get('value')
            unit = policy.get('unit', 'hours')

            if lookup_key in current:
                old_value = current[lookup_key]['value']
                if old_value != new_value:
                    changes.append({
                        'policy_type': policy_type,
                        'old_value': str(old_value),
                        'new_value': str(new_value),
                        'old_value_display': f"{old_value:.0f} {unit}",
                        'new_value_display': f"{new_value:.0f} {unit}",
                        'location_state': policy.get('location_state'),
                        'location_city': policy.get('location_city'),
                        'relevant_text': policy.get('relevant_text', ''),
                        'is_new': False
                    })
            else:
                # New policy (no current value)
                changes.append({
                    'policy_type': policy_type,
                    'old_value': '0',
                    'new_value': str(new_value),
                    'old_value_display': 'Not set',
                    'new_value_display': f"{new_value:.0f} {unit}",
                    'location_state': policy.get('location_state'),
                    'location_city': policy.get('location_city'),
                    'relevant_text': policy.get('relevant_text', ''),
                    'is_new': True
                })

        return changes

    async def generate_change_summary(self, change: Dict) -> str:
        """
        Generate a friendly summary of a policy change for employees.

        Args:
            change: Dictionary with change details

        Returns:
            Human-friendly summary string
        """
        if not self.client:
            # Fallback without API
            policy_name = POLICY_TYPES.get(
                change['policy_type'], {}
            ).get('name', change['policy_type'].replace('_', ' ').title())

            if change.get('is_new'):
                return f"New policy: {policy_name} is now {change['new_value_display']}."

            return f"{policy_name} changed from {change['old_value_display']} to {change['new_value_display']}."

        prompt = f"""Generate a friendly, simple explanation of this policy change for employees.
Keep it under 2 sentences. Use positive framing when possible.

Policy: {POLICY_TYPES.get(change['policy_type'], {}).get('name', change['policy_type'])}
Old Value: {change['old_value_display']}
New Value: {change['new_value_display']}
Relevant Text: {change.get('relevant_text', 'N/A')}

Example good responses:
- "Great news! Your sick time carryover limit is increasing to 80 hours."
- "Your vacation carryover maximum has been updated to 40 hours per year."
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception:
            # Fallback
            policy_name = POLICY_TYPES.get(
                change['policy_type'], {}
            ).get('name', change['policy_type'].replace('_', ' ').title())
            return f"{policy_name} changed from {change['old_value_display']} to {change['new_value_display']}."

    async def analyze_handbook(
        self,
        file_path: str,
        filename: str,
        uploaded_by: int,
        content: Optional[str] = None
    ) -> Tuple[HandbookUpload, List[Dict]]:
        """
        Full handbook analysis workflow.

        Args:
            file_path: Path to uploaded file
            filename: Original filename
            uploaded_by: User ID of uploader
            content: Pre-extracted text content (optional)

        Returns:
            Tuple of (HandbookUpload record, list of detected changes)
        """
        # Calculate file hash
        file_hash = self.calculate_file_hash(file_path)
        file_size = os.path.getsize(file_path)

        # Check for duplicate
        existing = self.check_for_duplicate(file_hash)
        detected_duplicate = existing.version if existing else None

        # Generate version
        version = self.get_next_version()

        # Create upload record
        upload = HandbookUpload(
            version=version,
            filename=filename,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            status='analyzing',
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            detected_duplicate_of=detected_duplicate
        )
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)

        try:
            # Get content if not provided
            if not content:
                # For now, assume text file. PDF parsing would need additional library.
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Binary file - would need PDF parsing
                    content = f"[Binary file: {filename}. PDF parsing not yet implemented.]"

            # Analyze with Claude
            analysis_result = await self.analyze_handbook_content(content)

            # Get current policies for comparison
            current_policies = self.get_current_policy_values()

            # Compare and detect changes
            extracted = analysis_result.get('policies', [])
            changes = self.compare_policies(extracted, current_policies)

            # Generate summaries for each change
            for change in changes:
                change['ai_summary'] = await self.generate_change_summary(change)

            # Update upload record
            upload.extracted_policies = {
                'policies': extracted,
                'changes': changes,
                'change_count': len(changes)
            }
            upload.ai_analysis = analysis_result
            upload.ai_summary = analysis_result.get('summary', '')
            upload.status = 'ready'

            if analysis_result.get('error'):
                upload.error_message = analysis_result['error']
                upload.status = 'error' if not extracted else 'ready'

            self.db.commit()
            self.db.refresh(upload)

            return upload, changes

        except Exception as e:
            upload.status = 'error'
            upload.error_message = str(e)
            self.db.commit()
            raise

    def publish_handbook(
        self,
        upload_id: int,
        admin_id: int,
        effective_date: Optional[date] = None,
        custom_reasons: Optional[Dict[str, str]] = None
    ) -> List[PolicyChangeLog]:
        """
        Publish handbook changes, creating PolicyChangeLog entries.

        Args:
            upload_id: ID of the HandbookUpload to publish
            admin_id: User ID of publishing admin
            effective_date: When changes take effect (defaults to today)
            custom_reasons: Dict mapping policy_type to custom reason text

        Returns:
            List of created PolicyChangeLog entries
        """
        stmt = select(HandbookUpload).where(HandbookUpload.id == upload_id)
        upload = self.db.execute(stmt).scalar_one_or_none()
        if not upload:
            raise ValueError(f"Handbook upload {upload_id} not found")

        if upload.status != 'ready':
            raise ValueError(f"Handbook not ready for publishing (status: {upload.status})")

        effective_date = effective_date or date.today()
        custom_reasons = custom_reasons or {}

        changes = upload.extracted_policies.get('changes', [])
        created_logs = []

        for change in changes:
            policy_type = change['policy_type']
            reason = custom_reasons.get(policy_type, change.get('relevant_text', ''))

            log = PolicyChangeLog.create_with_expiration(
                policy_type=policy_type,
                handbook_version=upload.version,
                old_value=change['old_value'],
                new_value=change['new_value'],
                old_value_display=change['old_value_display'],
                new_value_display=change['new_value_display'],
                effective_date=effective_date,
                changed_by=admin_id,
                location_state=change.get('location_state'),
                location_city=change.get('location_city'),
                reason=reason,
                ai_summary=change.get('ai_summary'),
                is_revert=False,
                handbook_upload_id=upload.id
            )
            self.db.add(log)
            created_logs.append(log)

        # Update upload status
        upload.status = 'published'
        upload.published_at = datetime.utcnow()
        upload.published_by = admin_id

        self.db.commit()

        return created_logs

    def revert_to_version(
        self,
        target_version: str,
        admin_id: int,
        effective_date: Optional[date] = None
    ) -> Tuple[HandbookUpload, List[PolicyChangeLog]]:
        """
        Revert policies to a previous handbook version.

        Args:
            target_version: Version string to revert to
            admin_id: User ID of admin performing revert
            effective_date: When revert takes effect

        Returns:
            Tuple of (new HandbookUpload for revert, list of PolicyChangeLogs)
        """
        stmt = select(HandbookUpload).where(
            HandbookUpload.version == target_version,
            HandbookUpload.status == 'published'
        )
        target = self.db.execute(stmt).scalar_one_or_none()

        if not target:
            raise ValueError(f"Published version {target_version} not found")

        stmt = select(HandbookUpload).where(
            HandbookUpload.status == 'published'
        ).order_by(HandbookUpload.published_at.desc())
        latest = self.db.execute(stmt).scalar_one_or_none()

        if not latest or latest.version == target_version:
            raise ValueError("Already at target version")

        effective_date = effective_date or date.today()
        new_version = self.get_next_version()

        # Create revert upload record
        revert_upload = HandbookUpload(
            version=new_version,
            filename=f"Revert to {target_version}",
            file_path=target.file_path,
            file_hash=target.file_hash,
            file_size=target.file_size,
            extracted_policies=target.extracted_policies,
            ai_analysis={'revert_from': latest.version, 'revert_to': target_version},
            ai_summary=f"Reverted from {latest.version} to {target_version}",
            status='published',
            uploaded_by=admin_id,
            uploaded_at=datetime.utcnow(),
            published_at=datetime.utcnow(),
            published_by=admin_id,
            is_revert_of=latest.id
        )
        self.db.add(revert_upload)
        self.db.commit()
        self.db.refresh(revert_upload)

        # Create change logs for the revert
        created_logs = []
        target_policies = target.extracted_policies.get('policies', [])
        latest_policies = latest.extracted_policies.get('policies', [])

        # Build lookup for latest policies
        latest_lookup = {
            (p['policy_type'], p.get('location_state'), p.get('location_city')): p
            for p in latest_policies
        }

        for policy in target_policies:
            key = (policy['policy_type'], policy.get('location_state'), policy.get('location_city'))
            latest_policy = latest_lookup.get(key, {})

            if latest_policy.get('value') != policy.get('value'):
                log = PolicyChangeLog.create_with_expiration(
                    policy_type=policy['policy_type'],
                    handbook_version=new_version,
                    old_value=str(latest_policy.get('value', 0)),
                    new_value=str(policy['value']),
                    old_value_display=f"{latest_policy.get('value', 0)} {policy.get('unit', 'hours')}",
                    new_value_display=f"{policy['value']} {policy.get('unit', 'hours')}",
                    effective_date=effective_date,
                    changed_by=admin_id,
                    location_state=policy.get('location_state'),
                    location_city=policy.get('location_city'),
                    reason=f"Reverted to {target_version}",
                    ai_summary=f"Policy reverted to previous value from version {target_version}.",
                    is_revert=True,
                    reverted_to_version=target_version,
                    handbook_upload_id=revert_upload.id
                )
                self.db.add(log)
                created_logs.append(log)

        self.db.commit()

        return revert_upload, created_logs
