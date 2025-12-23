---
name: pto-rag-knowledge
description: Build and maintain the RAG (Retrieval-Augmented Generation) knowledge base for PTO Central. Use when indexing documents, updating the knowledge base, or debugging RAG retrieval. Triggers on "RAG", "knowledge base", "index handbook", "policy search", "vector database", "doctrine", "embeddings", "ChromaDB".
---

# PTO RAG Knowledge Skill

## RAG Architecture

```
Documents -> Chunking -> Embedding -> ChromaDB -> Query -> Retrieval -> Response
```

## Index Locations

- **RAG Index**: `data/rag_index.json`
- **ChromaDB**: `data/chromadb/` (if using vector store)
- **Indexer Script**: `scripts/rag_indexer.py`

## Document Sources (Priority Order)

### 1. System Doctrine (Highest Priority)
```
task/
├── system_identity.md     # What is PTO Central
├── creator_profile.md     # Who created it
└── knowledge_contract.md  # RAG retrieval rules
```

### 2. Business Rules
```
.claude/rules/
├── business-rules.md      # Authoritative policies
└── protected-logic.md     # Protected code patterns

task/
└── formulalogic.md        # Calculation formulas
```

### 3. Help Documentation
```
data/help/
├── getting-started/
├── employees/
├── managers/
├── policies/
└── system/
```

## Indexing Configuration

```python
CHUNK_CONFIG = {
    "doctrine": {
        "chunk_size": 1000,
        "overlap": 200,
        "priority": "highest"
    },
    "rules": {
        "chunk_size": 800,
        "overlap": 150,
        "priority": "high"
    },
    "help": {
        "chunk_size": 500,
        "overlap": 100,
        "priority": "normal"
    }
}
```

## Rebuilding the RAG Index

```bash
# Full rebuild
venv\Scripts\python.exe scripts/rag_indexer.py --rebuild

# Incremental update
venv\Scripts\python.exe scripts/rag_indexer.py --update

# Verify index
venv\Scripts\python.exe -c "
import json
with open('data/rag_index.json') as f:
    idx = json.load(f)
print(f'Total chunks: {len(idx.get(\"entries\", idx))}')
"
```

## Doctrine Query Service

```python
from src.services.doctrine_query_service import get_doctrine_service

# Query the knowledge base
service = get_doctrine_service()
result = service.query("What is PTO Central?")

# Result structure
{
    "answer": "PTO Central is...",
    "source": "doctrine",  # doctrine, rules, help
    "confidence": "high",  # high, medium, low
    "source_file": "task/system_identity.md"
}
```

## Query Patterns

### Identity Queries (-> doctrine)
- "What is PTO Central?"
- "Who created this system?"
- "What can you do?"

### Policy Queries (-> rules)
- "What are the carryover rules?"
- "How much vacation do I get?"
- "What is Chicago Paid Leave?"

### How-To Queries (-> help)
- "How do I submit a request?"
- "How do I approve time off?"
- "How do I check my balance?"

## Prohibited Content Detection

The doctrine service validates responses:

```python
PROHIBITED_PATTERNS = [
    "i am conscious",
    "i am self-aware",
    "i feel",
    "i think therefore",
    "i have emotions",
    "i am sentient"
]

def validate_response(text: str) -> bool:
    """Returns False if response contains prohibited claims."""
    text_lower = text.lower()
    for pattern in PROHIBITED_PATTERNS:
        if pattern in text_lower:
            return False
    return True
```

## Adding New Documents

1. Place document in appropriate directory
2. Run indexer with `--update` flag
3. Verify chunk count increased
4. Test retrieval with sample query

```bash
# Add new help document
echo "# New Feature\n\nDocumentation here..." > data/help/features/new-feature.md

# Update index
venv\Scripts\python.exe scripts/rag_indexer.py --update

# Test retrieval
venv\Scripts\python.exe -c "
from src.services.doctrine_query_service import get_doctrine_service
result = get_doctrine_service().query('new feature')
print(result)
"
```

## RAG Index Structure

```json
{
    "version": "2.0",
    "created_at": "2025-12-23T10:00:00",
    "total_chunks": 418,
    "sources": {
        "doctrine": 45,
        "rules": 82,
        "help": 291
    },
    "entries": [
        {
            "id": "doc_001",
            "source": "task/system_identity.md",
            "category": "doctrine",
            "content": "PTO Central is an employee time-off...",
            "metadata": {
                "priority": "highest",
                "last_updated": "2025-12-23"
            }
        }
    ]
}
```

## MCP Integration

The RAG is accessible via MCP tools:

```python
# In mcp/pto_central_mcp.py
@mcp.tool()
def query_rag_corpus(query: str, category: str = None) -> dict:
    """
    Query the RAG knowledge base.

    Args:
        query: Natural language question
        category: Optional filter (doctrine, rules, help)

    Returns:
        Relevant knowledge chunks with sources
    """
    from src.services.doctrine_query_service import get_doctrine_service
    service = get_doctrine_service()
    return service.query(query, category=category)
```

## When to Use This Skill

- Adding new documentation to RAG
- Debugging retrieval issues
- Updating doctrine files
- Checking index health
- Optimizing chunk sizes
