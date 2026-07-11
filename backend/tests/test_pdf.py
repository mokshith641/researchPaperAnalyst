import pytest
from app.services.pdf_service import PDFService

def test_clean_text():
    """Test text cleaning strips spacing, resolves formatting and deletes null bytes."""
    dirty_text = "   This is  a   test   \n\n\nstring with \x00 null bytes and \n line breaks.   "
    expected = "This is a test string with null bytes and line breaks."
    assert PDFService.clean_text(dirty_text) == expected

def test_chunk_pages():
    """Test page chunking bounds chunks to their correct 1-based page numbers."""
    pages = [
        {"page_number": 1, "text": "Page one text content. It needs to be split properly."},
        {"page_number": 2, "text": "Page two text content. This page has different content."}
    ]
    
    # Let's chunk page text with small size to trigger splitting
    chunks = PDFService.chunk_pages(pages, chunk_size=20, chunk_overlap=0)
    
    assert len(chunks) > 0
    # Every chunk should contain page_number, chunk_index, and content
    for chunk in chunks:
        assert "page_number" in chunk
        assert "chunk_index" in chunk
        assert "content" in chunk
        assert len(chunk["content"]) <= 20
        
    # Verify mapping is accurate
    page_1_chunks = [c for c in chunks if c["page_number"] == 1]
    page_2_chunks = [c for c in chunks if c["page_number"] == 2]
    
    assert len(page_1_chunks) > 0
    assert len(page_2_chunks) > 0
    
    # Assert contents are derived from corresponding pages
    assert "Page one" in page_1_chunks[0]["content"]
    assert "Page two" in page_2_chunks[0]["content"]
