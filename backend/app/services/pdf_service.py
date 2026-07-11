import fitz  # PyMuPDF
import re
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

class PDFService:
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean extracted text from PDFs by removing invalid characters and correcting spaces."""
        # Remove null bytes first
        text = text.replace("\x00", "")
        # Replace multiple spaces/newlines with a single whitespace second
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def extract_text_by_page(cls, file_path: str) -> List[Dict[str, Any]]:
        """Open a PDF, read page contents, and output page structures."""
        pages_data = []
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                cleaned_text = cls.clean_text(text)
                
                # We skip empty pages
                if cleaned_text:
                    pages_data.append({
                        "page_number": page_num + 1,  # 1-based indexing for users
                        "text": cleaned_text
                    })
            doc.close()
        except Exception as e:
            raise RuntimeError(f"Failed to extract PDF text using PyMuPDF: {str(e)}")
            
        return pages_data

    @classmethod
    def chunk_pages(
        cls, pages: List[Dict[str, Any]], chunk_size: int = 1000, chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """Split text on a page-by-page basis to guarantee chunks are bound to a single page."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        all_chunks = []
        for page in pages:
            page_number = page["page_number"]
            page_text = page["text"]
            
            splits = splitter.split_text(page_text)
            for index, split_text in enumerate(splits):
                all_chunks.append({
                    "page_number": page_number,
                    "chunk_index": index,
                    "content": split_text
                })
                
        return all_chunks
