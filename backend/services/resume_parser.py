"""
Resume Parser Service for CareerLens AI
Extracts plain text and structured sections from PDF and DOCX files.
Handles error cases like corrupt files, empty content, and unsupported formats.
"""

import io
import re
from typing import Dict, Any, Tuple
import pymupdf  # PyMuPDF
import docx


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


class ResumeParserError(Exception):
    """Custom exception for resume parsing errors."""
    pass


def clean_text(text: str) -> str:
    """Normalizes whitespace and removes unwanted control characters."""
    if not text:
        return ""
    # Replace weird unicode spaces, tabs, bullet characters
    text = re.sub(r'[\r\t\f\v]', ' ', text)
    text = re.sub(r'[•●■◆▪\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' • ', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts raw text from a PDF byte buffer using PyMuPDF."""
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        if doc.page_count == 0:
            raise ResumeParserError("The uploaded PDF has 0 pages.")
        
        full_text = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")
            if page_text:
                full_text.append(page_text)
        
        doc.close()
        combined = "\n".join(full_text)
        if not combined.strip():
            raise ResumeParserError("The uploaded PDF contains no readable text. It may be a scanned image.")
        return clean_text(combined)
    except Exception as e:
        if isinstance(e, ResumeParserError):
            raise e
        raise ResumeParserError(f"Failed to parse PDF file: {str(e)}")


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text from a DOCX byte buffer using python-docx."""
    try:
        file_stream = io.BytesIO(file_bytes)
        doc = docx.Document(file_stream)
        
        full_text = []
        # Extract paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
                
        # Extract tables
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    full_text.append(" | ".join(row_text))
                    
        combined = "\n".join(full_text)
        if not combined.strip():
            raise ResumeParserError("The uploaded DOCX file is empty.")
        return clean_text(combined)
    except Exception as e:
        if isinstance(e, ResumeParserError):
            raise e
        raise ResumeParserError(f"Failed to parse DOCX file: {str(e)}")


def extract_text_from_file(filename: str, file_bytes: bytes) -> Tuple[str, str]:
    """
    Main parser entry point.
    Returns (extracted_text, file_type).
    """
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ResumeParserError("File exceeds maximum allowed size of 10 MB.")
        
    if not file_bytes:
        raise ResumeParserError("Uploaded file is empty (0 bytes).")
        
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes), "pdf"
    elif lower_name.endswith(".docx"):
        return extract_text_from_docx(file_bytes), "docx"
    elif lower_name.endswith(".txt"):
        try:
            text = file_bytes.decode("utf-8", errors="replace")
            return clean_text(text), "txt"
        except Exception as e:
            raise ResumeParserError(f"Failed to read TXT file: {str(e)}")
    else:
        raise ResumeParserError(f"Unsupported file format '{filename}'. Please upload a PDF (.pdf) or Word (.docx) document.")


def extract_sections(text: str) -> Dict[str, str]:
    """
    Splits resume text into canonical sections using heading detection.
    """
    sections = {
        "summary": "",
        "experience": "",
        "skills": "",
        "education": "",
        "projects": "",
        "certifications": "",
        "other": ""
    }

    section_patterns = {
        "summary": r"(?:professional\s+summary|executive\s+summary|summary|profile|about\s+me)\b",
        "experience": r"(?:work\s+experience|professional\s+experience|employment\s+history|experience|career\s+history)\b",
        "skills": r"(?:technical\s+skills|core\s+skills|skills\s+&?\s+technologies|skills|technologies|competencies)\b",
        "education": r"(?:education|academic\s+background|academics|degrees|qualification)\b",
        "projects": r"(?:technical\s+projects|key\s+projects|academic\s+projects|projects)\b",
        "certifications": r"(?:certifications|certificates|licenses|achievements)\b"
    }

    matches = []
    for sec_name, pattern in section_patterns.items():
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            # Check if this looks like a heading (e.g., at start of line or short line)
            start_pos = m.start()
            line_start = text.rfind('\n', 0, start_pos)
            prefix = text[line_start + 1:start_pos].strip()
            if len(prefix) < 15:  # Heading near start of line
                matches.append((start_pos, sec_name))

    matches.sort(key=lambda x: x[0])

    if not matches:
        # Fallback: estimate from text
        sections["summary"] = text[:300]
        sections["experience"] = text[300:]
        return sections

    for i, (start_idx, sec_name) in enumerate(matches):
        end_idx = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        content = text[start_idx:end_idx].strip()
        # Clean heading line from content
        first_newline = content.find('\n')
        if first_newline != -1:
            sections[sec_name] = content[first_newline:].strip()
        else:
            sections[sec_name] = content

    return sections
