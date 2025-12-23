"""
PTO Central RAG Indexer

Strictly follows config/rag_manifest.json Safe Corpus rules.
NO source code is indexed - only policy docs and help files.

Usage:
    python scripts/rag_indexer.py
"""

import json
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import glob as glob_module

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Load manifest
MANIFEST_PATH = PROJECT_ROOT / "config" / "rag_manifest.json"


def load_manifest() -> Dict[str, Any]:
    """Load and validate the RAG manifest."""
    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_allowed_files(manifest: Dict[str, Any]) -> List[Path]:
    """Get list of allowed files from manifest."""
    allowed_files = []

    # Policy Core
    for path in manifest['allow'].get('policy_core', []):
        full_path = PROJECT_ROOT / path
        if full_path.exists():
            allowed_files.append(full_path)
        else:
            print(f"  WARNING: {path} not found")

    # Math Invariants
    for path in manifest['allow'].get('math_invariants', []):
        full_path = PROJECT_ROOT / path
        if full_path.exists():
            allowed_files.append(full_path)
        else:
            print(f"  WARNING: {path} not found")

    # User Documentation (glob pattern)
    for pattern in manifest['allow'].get('user_documentation', []):
        matches = list(PROJECT_ROOT.glob(pattern))
        allowed_files.extend(matches)

    # Skills Knowledge (glob pattern)
    for pattern in manifest['allow'].get('skills_knowledge', []):
        matches = list(PROJECT_ROOT.glob(pattern))
        allowed_files.extend(matches)
        if matches:
            print(f"  Skills: {len(matches)} files from {pattern}")

    return allowed_files


def is_denied(filepath: Path, manifest: Dict[str, Any]) -> bool:
    """Check if a file is in the deny list."""
    # Normalize to forward slashes for cross-platform pattern matching
    rel_path = str(filepath.relative_to(PROJECT_ROOT)).replace('\\', '/')

    for category, patterns in manifest['deny'].items():
        for pattern in patterns:
            # Convert glob pattern to regex
            regex = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
            if re.match(regex, rel_path):
                return True

    return False


def chunk_markdown(content: str, filepath: Path, strategy: str = 'section-based') -> List[Dict[str, Any]]:
    """Split markdown content into chunks based on strategy."""
    chunks = []

    if strategy == 'single':
        # Entire document as one chunk
        chunks.append({
            'content': content,
            'chunk_index': 0,
            'total_chunks': 1
        })

    elif strategy in ['section-based', 'rule-based']:
        # Split on ## headings
        sections = re.split(r'\n(?=## )', content)
        for i, section in enumerate(sections):
            if section.strip():
                chunks.append({
                    'content': section.strip(),
                    'chunk_index': i,
                    'total_chunks': len(sections)
                })

    elif strategy == 'step-based':
        # Split on numbered lists
        steps = re.split(r'\n(?=\d+\. )', content)
        for i, step in enumerate(steps):
            if step.strip():
                chunks.append({
                    'content': step.strip(),
                    'chunk_index': i,
                    'total_chunks': len(steps)
                })

    elif strategy == 'formula-based':
        # Split on code blocks or formula sections
        parts = re.split(r'\n```', content)
        for i, part in enumerate(parts):
            if part.strip():
                chunks.append({
                    'content': part.strip(),
                    'chunk_index': i,
                    'total_chunks': len(parts)
                })

    else:
        # Default: section-based
        return chunk_markdown(content, filepath, 'section-based')

    return chunks


def determine_strategy(filepath: Path, manifest: Dict[str, Any]) -> str:
    """Determine chunking strategy for a file."""
    rel_path = str(filepath.relative_to(PROJECT_ROOT))

    chunking = manifest.get('chunking', {})

    # Check specific file matches
    for pattern, config in chunking.items():
        if '*' in pattern:
            # Glob pattern
            regex = pattern.replace('.', r'\.').replace('**/', '.*').replace('*', '[^/]*')
            if re.match(regex, rel_path):
                return config.get('strategy', 'section-based')
        else:
            # Exact match
            if rel_path.endswith(pattern):
                return config.get('strategy', 'section-based')

    return 'section-based'  # Default


def create_chunk_metadata(filepath: Path, chunk: Dict[str, Any], manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Create metadata for a chunk."""
    rel_path = str(filepath.relative_to(PROJECT_ROOT)).replace('\\', '/')

    # Directory-based category mapping
    HELP_CATEGORY_MAP = {
        'getting-started': 'Getting Started',
        'pto-requests': 'PTO Request Guide',
        'managers': 'Manager Guide',
        'admin': 'Admin Guide',
        'calendar': 'Calendar Guide',
        'technical': 'Technical Docs',
        'wfh-swap': 'WFH Swap Guide',
        'carryover': 'Carryover Guide',
        'reports': 'Reports Guide',
    }

    # Skills category mapping
    SKILLS_CATEGORY_MAP = {
        'pto-central-development': 'PTO Development Skill',
        'pto-policy-validator': 'Policy Validator Skill',
        'pto-agent-orchestrator': 'Agent Orchestrator Skill',
    }

    # Determine category based on path
    if 'skills/' in rel_path:
        # Extract skill name from path like "skills/pto-central-development/SKILL.md"
        parts = rel_path.split('/')
        if len(parts) >= 2:
            skill_name = parts[1]  # e.g., "pto-central-development"
            category = SKILLS_CATEGORY_MAP.get(skill_name, 'Skills Knowledge')
        else:
            category = 'Skills Knowledge'
        subcategory = 'skills'
    elif 'data/help/' in rel_path:
        # Extract subdirectory from path like "data/help/getting-started/file.md"
        parts = rel_path.split('/')
        if len(parts) >= 3:
            subdir = parts[2]  # e.g., "getting-started"
            category = HELP_CATEGORY_MAP.get(subdir, 'General Help')
        else:
            category = 'General Help'
        subcategory = 'help'
    elif '.claude/rules' in rel_path:
        category = 'Policy Rules'
        subcategory = 'governance'
    elif 'task/' in rel_path:
        category = 'Policy Formulas'
        subcategory = 'math'
    else:
        category = 'General Help'
        subcategory = 'other'

    # Get topic from filename
    topic = filepath.stem

    return {
        'source_file': rel_path,
        'category': category,
        'subcategory': subcategory,
        'topic': topic,
        'chunk_index': chunk['chunk_index'],
        'total_chunks': chunk['total_chunks'],
        'last_updated': datetime.now().isoformat(),
        'content_hash': hashlib.md5(chunk['content'].encode()).hexdigest()[:8]
    }


def validate_no_code(chunk_content: str) -> bool:
    """Validate chunk contains no source code patterns."""
    code_patterns = [
        r'^import\s+\w+',           # Python imports
        r'^from\s+\w+\s+import',    # Python from imports
        r'^def\s+\w+\s*\(',         # Function definitions
        r'^class\s+\w+',            # Class definitions
        r'@ui\.page\(',             # NiceGUI decorators
        r'db\.execute\(',           # Database calls
        r'session\.query\(',        # SQLAlchemy queries
    ]

    for pattern in code_patterns:
        if re.search(pattern, chunk_content, re.MULTILINE):
            return False

    return True


def run_indexer():
    """Main indexer function."""
    print("=" * 60)
    print("PTO Central RAG Indexer")
    print("=" * 60)
    print()

    # Load manifest
    print("Loading manifest from config/rag_manifest.json...")
    manifest = load_manifest()
    print(f"  Governance: {manifest.get('governance', 'unknown')}")
    print()

    # Get allowed files
    print("Scanning ALLOWED sources only...")
    allowed_files = get_allowed_files(manifest)
    print(f"  Found {len(allowed_files)} allowed files")
    print()

    # Filter out denied files
    print("Filtering against DENY list...")
    filtered_files = []
    denied_count = 0
    for f in allowed_files:
        if is_denied(f, manifest):
            print(f"  SKIPPED: {f.name}")
            denied_count += 1
        else:
            filtered_files.append(f)

    if denied_count > 0:
        print(f"  Filtered out {denied_count} file(s) matching deny patterns")
    else:
        print("  No files matched deny patterns")
    print()
    allowed_files = filtered_files

    # Process files and create chunks
    print("Creating chunks from Safe Corpus...")
    all_chunks = []
    total_size = 0

    for filepath in allowed_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            total_size += len(content)
            strategy = determine_strategy(filepath, manifest)
            chunks = chunk_markdown(content, filepath, strategy)

            for chunk in chunks:
                # Validate no code
                if not validate_no_code(chunk['content']):
                    print(f"  WARNING: Code detected in {filepath}, skipping chunk")
                    continue

                metadata = create_chunk_metadata(filepath, chunk, manifest)
                all_chunks.append({
                    'id': f"{metadata['source_file']}#{metadata['chunk_index']}",
                    'content': chunk['content'],
                    'metadata': metadata
                })

        except Exception as e:
            print(f"  ERROR processing {filepath}: {e}")

    print(f"  Created {len(all_chunks)} chunks from {len(allowed_files)} files")
    print(f"  Total text size: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    print()

    # Save index
    index_path = PROJECT_ROOT / "data" / "rag_index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    index_data = {
        'version': '1.0.0',
        'created': datetime.now().isoformat(),
        'manifest': str(MANIFEST_PATH),
        'statistics': {
            'total_files': len(allowed_files),
            'total_chunks': len(all_chunks),
            'total_bytes': total_size
        },
        'chunks': all_chunks
    }

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2)

    print(f"Index saved to: {index_path}")
    print()

    return index_data


def generate_audit_report(index_data: Dict[str, Any]):
    """Generate content audit report."""
    print("=" * 60)
    print("CONTENT AUDIT REPORT")
    print("=" * 60)
    print()

    chunks = index_data['chunks']
    stats = index_data['statistics']

    print(f"Total chunks created: {stats['total_chunks']}")
    print(f"Total files indexed: {stats['total_files']}")
    print(f"Total index size: {stats['total_bytes']:,} bytes ({stats['total_bytes']/1024:.1f} KB)")
    print()

    # Verify size is reasonable (should be ~150-300KB for 40 files)
    if stats['total_bytes'] < 50000:
        print("WARNING: Index seems too small")
    elif stats['total_bytes'] > 500000:
        print("WARNING: Index seems too large - may include unexpected files")
    else:
        print("OK: Index size is within expected range (50KB-500KB)")
    print()

    # Random sample of 3 chunks
    import random
    print("RANDOM SAMPLE (3 chunks to verify Safe Corpus):")
    print("-" * 60)

    sample_indices = random.sample(range(len(chunks)), min(3, len(chunks)))

    for i, idx in enumerate(sample_indices, 1):
        chunk = chunks[idx]
        print(f"\nSample {i}:")
        print(f"  Source: {chunk['metadata']['source_file']}")
        print(f"  Category: {chunk['metadata']['category']}")
        print(f"  Preview: {chunk['content'][:200]}...")

        # Verify it's not code
        if validate_no_code(chunk['content']):
            print("  CODE CHECK: PASS (no source code detected)")
        else:
            print("  CODE CHECK: FAIL (source code detected!)")

    print()
    print("-" * 60)

    # Category breakdown
    print("\nCATEGORY BREAKDOWN:")
    categories = {}
    for chunk in chunks:
        cat = chunk['metadata']['category']
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} chunks")

    print()
    print("=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    index_data = run_indexer()
    if index_data:
        generate_audit_report(index_data)
