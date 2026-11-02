"""Shared input and scope checks used by multiple thin experiment entries."""
import json
from pathlib import Path


def load_documents(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def within_project(documents, project_id):
    return [doc for doc in documents if doc['project_id'] == project_id]


def invalid_citations(citation_ids, documents, project_id):
    allowed = {doc['id'] for doc in within_project(documents, project_id)}
    return [ident for ident in citation_ids if ident not in allowed]
