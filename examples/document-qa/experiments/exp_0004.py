from pathlib import Path
from shared.documents import invalid_citations, load_documents

documents = load_documents(Path(__file__).resolve().parents[1] / 'data/demo-documents.json')
assert invalid_citations(['A', 'B', 'missing'], documents, 'alpha') == ['B', 'missing']
assert invalid_citations(['A', 'C'], documents, 'alpha') == []
print('Demo citation checks passed: reject outside-project and unknown citations.')
