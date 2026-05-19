from uuid import uuid4

from app.domain.models.document import Document, DocumentChunk


def test_create_document_chunk():
    doc_id = uuid4()
    chunk = DocumentChunk(
        document_id=doc_id,
        text="Sample text",
        page_number=1,
        chunk_index=0,
    )
    assert chunk.text == "Sample text"
    assert chunk.page_number == 1
    assert chunk.chunk_index == 0
    assert chunk.document_id == doc_id


def test_create_document():
    doc = Document(filename="test.pdf", extraction_method="text")
    assert doc.filename == "test.pdf"
    assert doc.extraction_method == "text"
    assert doc.chunks == []

    chunk = DocumentChunk(
        document_id=doc.id,
        text="Sample text",
        page_number=1,
        chunk_index=0,
    )
    doc.add_chunk(chunk)
    assert len(doc.chunks) == 1
    assert doc.chunks[0] == chunk
