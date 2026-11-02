from pathlib import Path
from shared.documents import load_documents, within_project

documents = load_documents(Path(__file__).resolve().parents[1] / 'data/demo-documents.json')
selected = within_project(documents, 'alpha')
assert [doc['id'] for doc in selected] == ['A', 'C']
print('Demo scope check passed: alpha contains A and C; excludes beta document B.')
