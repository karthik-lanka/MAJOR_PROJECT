"""
Unit tests for the chunking service.
"""

from app.services.chunking_service import ChunkingService, PageText


def test_chunking_service_initialization():
    service = ChunkingService()
    assert service.chunk_size > 0
    assert service.chunk_overlap >= 0


def test_chunking_short_text():
    service = ChunkingService()
    text = "Artificial intelligence is the intelligence of machines or software."
    chunks = service.chunk_text(text, source_page=1)
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_number == 1


def test_chunking_multiple_pages():
    service = ChunkingService()
    pages = [
        PageText(text=f"This is page {i} content discussing algorithms.", page_number=i)
        for i in range(1, 5)
    ]
    chunks = service.chunk_pages(pages)
    assert len(chunks) >= 1
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert len(chunk.text) > 0
        assert chunk.content_hash
