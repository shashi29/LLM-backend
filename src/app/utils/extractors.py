import io
import logging
import os
import re
from typing import List, Optional, Dict, Union, Tuple, Any
from dataclasses import dataclass
from functools import wraps
import json
import tempfile
from pathlib import Path
import subprocess
import string
import mimetypes

# Third-party imports for PDF processing
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
import pikepdf

# Third-party imports for Word document processing
try:
    from docx import Document
    import docx.opc.exceptions
    from docx.document import Document as DocxDocument
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table, _Cell
    from docx.text.paragraph import Paragraph
    PYTHON_DOCX_INSTALLED = True
except ImportError:
    PYTHON_DOCX_INSTALLED = False

# Optional: For image enhancement before OCR
try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_INSTALLED = True
except ImportError:
    PIL_INSTALLED = False

# Optional: For advanced PDF extraction
try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    from pdfminer.layout import LAParams
    PDFMINER_INSTALLED = True
except ImportError:
    PDFMINER_INSTALLED = False

# Optional: For additional document extraction methods
try:
    import textract
    TEXTRACT_INSTALLED = True
except ImportError:
    TEXTRACT_INSTALLED = False

# Optional: For MIME type detection
try:
    import magic
    MAGIC_INSTALLED = True
except ImportError:
    MAGIC_INSTALLED = False


@dataclass
class PageContent:
    """Data class to store extracted page content with metadata."""
    text: str
    page_number: int
    metadata: Optional[Dict] = None


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def exception_handler(func):
    """Decorator to handle exceptions in extraction functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return []
    return wrapper


class DocumentExtractor:
    """
    Production-grade document text extractor that handles PDF and Word documents.
    Combines multiple extraction methods including direct text extraction,
    PDF parsing, and OCR capabilities for scanned documents.
    """
    
    def __init__(self, 
                 ocr_lang: str = 'eng', 
                 dpi: int = 300,
                 use_ocr_fallback: bool = True,
                 extraction_methods: Optional[List[str]] = None):
        """
        Initialize the document extractor.
        
        Args:
            ocr_lang (str): Language for OCR (default: 'eng')
            dpi (int): DPI for image conversion during OCR (default: 300)
            use_ocr_fallback (bool): Whether to use OCR as fallback (default: True)
            extraction_methods (List[str]): List of extraction methods to try, in order
                                           (default: all available methods)
        """
        self.ocr_lang = ocr_lang
        self.dpi = dpi
        self.use_ocr_fallback = use_ocr_fallback
        
        # Default extraction methods in order of preference
        default_methods = []
        if PDFMINER_INSTALLED:
            default_methods.append("pdfminer")
        default_methods.append("pdfplumber")
        if PIL_INSTALLED and pytesseract:
            default_methods.append("ocr")
            
        self.extraction_methods = extraction_methods or default_methods
        
        # Check required dependencies
        if not PIL_INSTALLED:
            logger.warning("PIL not installed. Image preprocessing will be limited.")
        if not PYTHON_DOCX_INSTALLED:
            logger.warning("python-docx not installed. Word document extraction will be limited.")
        if not PDFMINER_INSTALLED:
            logger.warning("pdfminer.six not installed. Some PDF extraction features will be limited.")
        if not TEXTRACT_INSTALLED:
            logger.warning("textract not installed. Alternative document extraction will be limited.")
    
    def _enhance_image(self, image: 'Image') -> 'Image':
        if not PIL_INSTALLED:
            return image

        image = image.convert('L')
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        image = image.filter(ImageFilter.SHARPEN)
        image = image.point(lambda x: 0 if x < 128 else 255, '1')
        
        return image
    
    def _preprocess_text(self, text: str) -> str:
        if not text:
            return ""
        
        text = ''.join(c for c in text if c in string.printable)
        
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(line for line in lines if line)
        
        return text
        
    def _perform_ocr(self, image_path: str) -> str:
        try:
            image = Image.open(image_path)
            enhanced_image = self._enhance_image(image)
            
            custom_config = f'--oem 3 --psm 6 -l {self.ocr_lang}'
            text = pytesseract.image_to_string(enhanced_image, config=custom_config)
            return self._preprocess_text(text)
        except Exception as e:
            logger.error(f"OCR failed: {str(e)}")
            return ""
    
    def _should_use_ocr(self, text: str) -> bool:
        if not self.use_ocr_fallback:
            return False
            
        if not text or text.isspace():
            return True
            
        # If the text is very short, likely it's not complete
        if len(text.strip()) < 100:
            return True
            
        # Check if text contains a large number of unrecognizable characters
        unreadable_chars = sum(1 for c in text if not c.isalnum() and not c.isspace() and c not in '.,;:!?-()[]{}"\'')
        if unreadable_chars / len(text) > 0.2:  # More than 20% unreadable
            return True
            
        return False
    
    def _extract_pdf_metadata(self, pdf_path: str) -> Dict:
        metadata = {}
        
        try:
            with pikepdf.open(pdf_path) as pdf:
                if hasattr(pdf, 'docinfo') and pdf.docinfo:
                    for key, value in pdf.docinfo.items():
                        if str(value):
                            # Clean up key name (remove '/' prefix if present)
                            clean_key = str(key).replace('/', '')
                            metadata[clean_key] = str(value)
                
                # Also extract XMP metadata if available
                if hasattr(pdf, 'Root') and '/Metadata' in pdf.Root:
                    try:
                        metadata['has_xmp'] = True
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata using pikepdf: {str(e)}")
        
        # Try using pdfplumber as a fallback
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if hasattr(pdf, 'metadata') and pdf.metadata:
                    for key, value in pdf.metadata.items():
                        if value:
                            # Clean up key name (remove '/' prefix if present)
                            clean_key = key[1:] if key.startswith('/') else key
                            metadata[clean_key] = value
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata using pdfplumber: {str(e)}")
        
        return metadata
    
    def _extract_page_text_with_pdfminer(self, pdf_path: str, page_num: int) -> str:
        if not PDFMINER_INSTALLED:
            return ""
            
        try:
            output = io.StringIO()
            with open(pdf_path, 'rb') as fp:
                from pdfminer.converter import TextConverter
                from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
                from pdfminer.pdfpage import PDFPage
                from pdfminer.layout import LAParams
                
                rsrcmgr = PDFResourceManager()
                device = TextConverter(rsrcmgr, output, laparams=LAParams())
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                
                for i, page in enumerate(PDFPage.get_pages(fp, set([page_num - 1]), maxpages=1)):
                    interpreter.process_page(page)
                    
                device.close()
                
                return self._preprocess_text(output.getvalue())
        except Exception as e:
            logger.warning(f"pdfminer extraction failed for page {page_num}: {str(e)}")
            return ""
    
    def _extract_page_text_with_pdfplumber(self, pdf: 'pdfplumber.PDF', page_num: int) -> str:
        try:
            page = pdf.pages[page_num - 1]
            text = page.extract_text() or ""
            return self._preprocess_text(text)
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed for page {page_num}: {str(e)}")
            return ""
    
    def _get_page_structure_info(self, page: Any) -> Dict:
        structure_info = {}
        
        try:
            # Count elements on the page
            if hasattr(page, 'chars') and page.chars:
                structure_info['char_count'] = len(page.chars)
            
            if hasattr(page, 'lines') and page.lines:
                structure_info['line_count'] = len(page.lines)
            
            if hasattr(page, 'rects') and page.rects:
                structure_info['rect_count'] = len(page.rects)
            
            if hasattr(page, 'curves') and page.curves:
                structure_info['curve_count'] = len(page.curves)
            
            if hasattr(page, 'images') and page.images:
                structure_info['image_count'] = len(page.images)
                structure_info['has_images'] = True
            else:
                structure_info['has_images'] = False
                
            if hasattr(page, 'width') and page.width:
                structure_info['width'] = page.width
                
            if hasattr(page, 'height') and page.height:
                structure_info['height'] = page.height
            
            # Detect if the page is likely a scanned image
            if structure_info.get('image_count', 0) > 0 and structure_info.get('char_count', 0) < 10:
                structure_info['likely_scanned'] = True
            else:
                structure_info['likely_scanned'] = False
                
        except Exception as e:
            logger.warning(f"Failed to extract page structure: {str(e)}")
            
        return structure_info
    
    @exception_handler
    def extract_from_pdf(self, pdf_path: str) -> List[PageContent]:
        pages = []
        
        # Ensure the file exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return pages
            
        # Extract PDF metadata
        try:
            pdf_metadata = self._extract_pdf_metadata(pdf_path)
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata: {str(e)}")
            pdf_metadata = {}
        
        # Initialize pdfplumber PDF object outside the loop
        pdf = None
        total_pages = 0
        
        try:
            pdf = pdfplumber.open(pdf_path)
            total_pages = len(pdf.pages)
            pdf_metadata['total_pages'] = total_pages
        except Exception as e:
            logger.error(f"Failed to open PDF with pdfplumber: {str(e)}")
            # Try to get total pages in a different way
            try:
                with pikepdf.open(pdf_path) as pikepdf_doc:
                    total_pages = len(pikepdf_doc.pages)
                    pdf_metadata['total_pages'] = total_pages
            except Exception:
                # Default to 1 if we can't determine the number of pages
                total_pages = 1
                pdf_metadata['total_pages'] = 1
                pdf_metadata['page_count_estimation'] = True
        
        # Process each page
        for page_num in range(1, total_pages + 1):
            logger.info(f"Processing page {page_num} of {total_pages}")
            
            # Initialize page metadata
            page_metadata = {
                **pdf_metadata,
                "page_number": page_num
            }
            
            # Get page structure if possible
            if pdf:
                try:
                    page = pdf.pages[page_num - 1]
                    page_structure = self._get_page_structure_info(page)
                    page_metadata.update(page_structure)
                except Exception as e:
                    logger.warning(f"Failed to get page structure for page {page_num}: {str(e)}")
            
            # Try each extraction method in sequence
            text = ""
            extraction_method = "none"
            
            # Method 1: Try pdfminer if available
            if not text and "pdfminer" in self.extraction_methods and PDFMINER_INSTALLED:
                try:
                    logger.info(f"Trying pdfminer for page {page_num}")
                    pdfminer_text = self._extract_page_text_with_pdfminer(pdf_path, page_num)
                    if pdfminer_text and pdfminer_text.strip():
                        text = pdfminer_text
                        extraction_method = "pdfminer"
                        logger.info(f"pdfminer extraction successful for page {page_num}")
                    else:
                        logger.warning(f"pdfminer returned empty text for page {page_num}")
                except Exception as e:
                    logger.warning(f"pdfminer extraction failed for page {page_num}: {str(e)}")
            
            # Method 2: Try pdfplumber if text is still empty
            if not text and "pdfplumber" in self.extraction_methods and pdf:
                try:
                    logger.info(f"Trying pdfplumber for page {page_num}")
                    pdfplumber_text = self._extract_page_text_with_pdfplumber(pdf, page_num)
                    if pdfplumber_text and pdfplumber_text.strip():
                        text = pdfplumber_text
                        extraction_method = "pdfplumber"
                        logger.info(f"pdfplumber extraction successful for page {page_num}")
                    else:
                        logger.warning(f"pdfplumber returned empty text for page {page_num}")
                except Exception as e:
                    logger.warning(f"pdfplumber extraction failed for page {page_num}: {str(e)}")
            
            # Method 3: Try OCR as a last resort
            if not text and "ocr" in self.extraction_methods and self.use_ocr_fallback:
                try:
                    logger.info(f"Trying OCR for page {page_num}")
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Convert page to image
                        try:
                            images = convert_from_path(
                                pdf_path, 
                                dpi=self.dpi, 
                                first_page=page_num, 
                                last_page=page_num
                            )
                            
                            if images:
                                temp_img_path = os.path.join(temp_dir, f"page_{page_num}.png")
                                images[0].save(temp_img_path)
                                
                                # Perform OCR
                                ocr_text = self._perform_ocr(temp_img_path)
                                
                                if ocr_text and ocr_text.strip():
                                    text = ocr_text
                                    extraction_method = "ocr"
                                    logger.info(f"OCR extraction successful for page {page_num}")
                                else:
                                    logger.warning(f"OCR returned empty text for page {page_num}")
                            else:
                                logger.warning(f"Failed to convert page {page_num} to image")
                        except Exception as ocr_err:
                            logger.warning(f"Error during OCR processing for page {page_num}: {str(ocr_err)}")
                except Exception as e:
                    logger.warning(f"OCR extraction failed for page {page_num}: {str(e)}")
            
            # Record the extraction method used
            page_metadata["extraction_method"] = extraction_method
            
            # Add the page to results
            if text and text.strip():
                text_to_add = text.strip()
                logger.info(f"Adding page {page_num} with {len(text_to_add)} characters of text")
                pages.append(PageContent(
                    text=text_to_add,
                    page_number=page_num,
                    metadata=page_metadata
                ))
            else:
                logger.warning(f"No text extracted for page {page_num} using any method")
                pages.append(PageContent(
                    text="",
                    page_number=page_num,
                    metadata={**page_metadata, "extraction_failed": True}
                ))
        
        # Clean up
        if pdf:
            pdf.close()
        
        # If all methods failed and we have no pages with content, try direct OCR recovery
        if all(not p.text for p in pages) and "ocr" in self.extraction_methods and self.use_ocr_fallback:
            logger.info("All extraction methods failed, attempting direct OCR recovery")
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Convert entire PDF to images
                    images = convert_from_path(pdf_path, dpi=self.dpi)
                    
                    # Clear previous empty pages
                    pages = []
                    
                    for i, image in enumerate(images, 1):
                        temp_img_path = os.path.join(temp_dir, f"recovery_page_{i}.png")
                        image.save(temp_img_path)
                        
                        # Perform OCR
                        recovery_text = self._perform_ocr(temp_img_path)
                        
                        # Create recovery metadata
                        recovery_metadata = {
                            "page_number": i,
                            "extraction_method": "direct_ocr_recovery",
                            "recovery_mode": True
                        }
                        
                        if recovery_text and recovery_text.strip():
                            text_to_add = recovery_text.strip()
                            logger.info(f"Recovery: Adding page {i} with {len(text_to_add)} characters of text")
                            pages.append(PageContent(
                                text=text_to_add,
                                page_number=i,
                                metadata=recovery_metadata
                            ))
                        else:
                            logger.warning(f"Recovery: No text extracted for page {i}")
                            pages.append(PageContent(
                                text="",
                                page_number=i,
                                metadata={**recovery_metadata, "extraction_failed": True}
                            ))
            except Exception as recovery_error:
                logger.error(f"OCR recovery also failed: {str(recovery_error)}")
        
        # If we still have no pages, ensure we return at least one empty page
        if not pages:
            logger.warning("All extraction methods failed, returning empty page")
            pages.append(PageContent(
                text="",
                page_number=1,
                metadata={"extraction_failed": True, "reason": "all_methods_failed"}
            ))
        
        return pages

    def _iterate_docx_items(self, parent):
        if not PYTHON_DOCX_INSTALLED:
            return
            
        if isinstance(parent, DocxDocument):
            parent_elm = parent.element.body
        elif isinstance(parent, _Cell):
            parent_elm = parent._tc
        else:
            raise ValueError(f"Unsupported parent type: {type(parent)}")
            
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)
    
    def _extract_docx_text(self, doc: 'DocxDocument') -> List[str]:
        if not PYTHON_DOCX_INSTALLED:
            return []
            
        text_parts = []
        
        try:
            # Process all items in the document
            for item in doc.paragraphs:
                if item.text.strip():
                    text_parts.append(item.text.strip())
                    
            # Process all tables in the document
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if paragraph.text.strip():
                                text_parts.append(paragraph.text.strip())
        except Exception as e:
            logger.warning(f"Error extracting text from docx: {str(e)}")
            
        return text_parts
    
    def _extract_word_metadata(self, doc: 'DocxDocument') -> Dict:
        if not PYTHON_DOCX_INSTALLED:
            return {}
            
        metadata = {}
        
        try:
            # Core properties
            if hasattr(doc, 'core_properties'):
                core_props = doc.core_properties
                for attr in ['author', 'category', 'comments', 'content_status', 
                           'created', 'identifier', 'keywords', 'language', 
                           'last_modified_by', 'last_printed', 'modified', 
                           'revision', 'subject', 'title', 'version']:
                    if hasattr(core_props, attr):
                        value = getattr(core_props, attr)
                        if value is not None:
                            metadata[attr] = str(value)
            
            # Document statistics
            metadata['paragraph_count'] = len(doc.paragraphs)
            metadata['table_count'] = len(doc.tables)
            
            # Section information
            if doc.sections:
                first_section = doc.sections[0]
                metadata['page_width'] = first_section.page_width.pt
                metadata['page_height'] = first_section.page_height.pt
                metadata['section_count'] = len(doc.sections)
        
        except Exception as e:
            logger.warning(f"Failed to extract Word metadata: {str(e)}")
            
        return metadata
    
    def _estimate_page_breaks(self, paragraphs: List[str], page_height_chars: int = 3000) -> List[List[str]]:
        pages = []
        current_page = []
        current_char_count = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # Check if adding this paragraph would exceed page capacity
            if current_char_count + para_length > page_height_chars and current_page:
                pages.append(current_page)
                current_page = [para]
                current_char_count = para_length
            else:
                current_page.append(para)
                current_char_count += para_length
        
        if current_page:
            pages.append(current_page)
            
        return pages
    
    def _detect_page_breaks(self, paragraphs: List[str]) -> List[int]:
        break_indices = []
        
        for i, para in enumerate(paragraphs):
            # Look for common page break indicators
            if (re.search(r'PAGE\s*BREAK', para, re.IGNORECASE) or 
                para == '\f' or  # Form feed character
                re.match(r'^-{3,}$', para) or  # Series of hyphens
                re.match(r'^_{3,}$', para)):  # Series of underscores
                break_indices.append(i)
                
        return break_indices
    
    def _detect_file_type(self, file_path: str) -> str:
        # Try using python-magic if available
        if MAGIC_INSTALLED:
            try:
                mime = magic.Magic(mime=True)
                detected_type = mime.from_file(file_path)
                logger.info(f"Detected file type: {detected_type} for {file_path}")
                return detected_type
            except Exception as e:
                logger.warning(f"Error detecting file type with python-magic: {str(e)}")
        
        # Fallback to mimetypes module
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            logger.info(f"Guessed MIME type: {mime_type} for {file_path}")
            return mime_type
        
        # Last resort: use file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.docx':
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif ext == '.doc':
            return 'application/msword'
        elif ext == '.pdf':
            return 'application/pdf'
        else:
            return 'application/octet-stream'
    
    @exception_handler
    def extract_from_doc(self, doc_path: str) -> List[PageContent]:
        if not os.path.exists(doc_path):
            logger.error(f"Document not found: {doc_path}")
            return []
        
        # Detect actual file type
        file_type = self._detect_file_type(doc_path)
        logger.info(f"Processing document: {doc_path}, detected type: {file_type}")
        
        # Basic metadata
        file_metadata = {
            "file_path": doc_path,
            "detected_type": file_type
        }
        
        # Try multiple extraction methods in sequence
        extraction_methods = [
            self._extract_with_python_docx,
            self._extract_with_textract,
            self._extract_with_libre_office, 
            self._extract_with_antiword,
            self._extract_with_strings_cmd
        ]
        
        for method in extraction_methods:
            method_name = method.__name__
            try:
                logger.info(f"Trying {method_name} for {doc_path}")
                pages = method(doc_path)
                
                # Check if extraction produced any content
                if pages and any(page.text.strip() for page in pages):
                    logger.info(f"Successfully extracted {len(pages)} pages using {method_name}")
                    
                    # Update metadata to include the successful method
                    for page in pages:
                        if page.metadata is None:
                            page.metadata = {}
                        page.metadata.update({
                            "extraction_method": method_name,
                            **file_metadata
                        })
                    
                    return pages
                else:
                    logger.warning(f"{method_name} returned no content")
            
            except Exception as e:
                logger.warning(f"{method_name} failed: {str(e)}")
                continue
        
        # If all methods failed, return a single empty page with error metadata
        logger.error(f"All extraction methods failed for {doc_path}")
        return [PageContent(
            text="",
            page_number=1,
            metadata={
                "extraction_failed": True,
                "reason": "all_methods_failed",
                **file_metadata
            }
        )]
    
    def _extract_with_python_docx(self, doc_path: str) -> List[PageContent]:
        if not PYTHON_DOCX_INSTALLED:
            logger.error("python-docx not installed")
            return []
        
        try:
            # Try to open as a .docx file
            doc = Document(doc_path)
            
            # Extract metadata
            metadata = self._extract_word_metadata(doc)
            
            # Extract all text paragraphs
            paragraphs = self._extract_docx_text(doc)
            
            if not paragraphs:
                logger.warning(f"No paragraphs extracted from {doc_path}")
                return []
            
            # Detect page breaks
            break_indices = self._detect_page_breaks(paragraphs)
            
            # Create pages
            pages = []
            
            if break_indices:
                # Use detected page breaks
                current_page = 1
                start_idx = 0
                
                for break_idx in break_indices:
                    page_paragraphs = paragraphs[start_idx:break_idx]
                    
                    if page_paragraphs:
                        pages.append(PageContent(
                            text='\n'.join(page_paragraphs),
                            page_number=current_page,
                            metadata={
                                **metadata,
                                "page_break_detection": "explicit"
                            }
                        ))
                    
                    current_page += 1
                    start_idx = break_idx + 1
                
                # Add last page
                if start_idx < len(paragraphs):
                    page_paragraphs = paragraphs[start_idx:]
                    
                    if page_paragraphs:
                        pages.append(PageContent(
                            text='\n'.join(page_paragraphs),
                            page_number=current_page,
                            metadata={
                                **metadata,
                                "page_break_detection": "explicit"
                            }
                        ))
            else:
                # Estimate page breaks based on character count
                page_height_chars = 3000  # Default
                
                if 'page_height' in metadata and 'page_width' in metadata:
                    # Rough estimate based on page dimensions
                    area = metadata['page_height'] * metadata['page_width']
                    page_height_chars = int(area / 20)  # Adjust as needed
                
                # Split paragraphs into pages
                page_contents = self._estimate_page_breaks(paragraphs, page_height_chars)
                
                for i, page_paragraphs in enumerate(page_contents, 1):
                    pages.append(PageContent(
                        text='\n'.join(page_paragraphs),
                        page_number=i,
                        metadata={
                            **metadata,
                            "page_break_detection": "estimated",
                            "chars_per_page": page_height_chars
                        }
                    ))
            
            return pages
            
        except (ValueError, docx.opc.exceptions.PackageNotFoundError) as e:
            logger.warning(f"python-docx failed: {str(e)}")
            raise
    
    def _extract_with_textract(self, doc_path: str) -> List[PageContent]:
        if not TEXTRACT_INSTALLED:
            logger.error("textract not installed")
            raise ImportError("textract not installed")
        
        try:
            # Extract text using textract
            text = textract.process(doc_path).decode('utf-8', errors='ignore')
            
            if not text.strip():
                logger.warning(f"textract returned empty text for {doc_path}")
                return []
            
            # Split by form feeds or other page break indicators
            page_texts = re.split(r'\f|\n\s*\[\s*Page\s+\d+\s*\]', text)
            
            # Filter out empty pages
            page_texts = [page.strip() for page in page_texts if page.strip()]
            
            pages = []
            
            # Create page objects
            for i, page_text in enumerate(page_texts, 1):
                pages.append(PageContent(
                    text=page_text,
                    page_number=i,
                    metadata={
                        "extraction_library": "textract"
                    }
                ))
            
            # If no pages were split, create a single page
            if not pages and text.strip():
                pages = [PageContent(
                    text=text.strip(),
                    page_number=1,
                    metadata={
                        "extraction_library": "textract",
                        "page_break_detection": "none"
                    }
                )]
            
            return pages
            
        except Exception as e:
            logger.warning(f"textract extraction failed: {str(e)}")
            raise
    
    def _extract_with_libre_office(self, doc_path: str) -> List[PageContent]:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert to PDF using LibreOffice or OpenOffice
                pdf_path = os.path.join(temp_dir, "converted.pdf")
                
                # Try different conversion commands
                conversion_commands = [
                    ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", temp_dir, doc_path],
                    ["soffice", "--headless", "--convert-to", "pdf", "--outdir", temp_dir, doc_path],
                    ["unoconv", "-f", "pdf", "-o", pdf_path, doc_path]
                ]
                
                conversion_success = False
                
                for cmd in conversion_commands:
                    try:
                        logger.info(f"Trying conversion with: {' '.join(cmd)}")
                        result = subprocess.run(cmd, check=True, capture_output=True, timeout=60)
                        
                        # Check if conversion created the PDF
                        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                            conversion_success = True
                            logger.info(f"Successfully converted {doc_path} to PDF using {cmd[0]}")
                            break
                        else:
                            # Look for any PDF in the temp dir (command might use different naming)
                            pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
                            if pdf_files:
                                pdf_path = os.path.join(temp_dir, pdf_files[0])
                                conversion_success = True
                                logger.info(f"Found converted PDF: {pdf_path}")
                                break
                    
                    except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
                        logger.warning(f"Conversion with {cmd[0]} failed: {str(e)}")
                
                if not conversion_success:
                    logger.error("All conversion methods failed")
                    raise RuntimeError("Document conversion failed")
                
                # Extract text from the PDF
                pages = self.extract_from_pdf(pdf_path)
                
                # Update metadata to indicate conversion
                for page in pages:
                    if page.metadata is None:
                        page.metadata = {}
                    page.metadata["converted_from_doc"] = True
                
                return pages
        
        except Exception as e:
            logger.warning(f"LibreOffice conversion failed: {str(e)}")
            raise
    
    def _extract_with_antiword(self, doc_path: str) -> List[PageContent]:
        try:
            # Check if antiword is installed
            subprocess.run(["which", "antiword"], check=True, capture_output=True)
            
            with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
                # Run antiword
                subprocess.run(
                    ["antiword", doc_path],
                    stdout=temp_file,
                    stderr=subprocess.PIPE,
                    check=True
                )
                
                # Read output
                temp_file.seek(0)
                text = temp_file.read().decode('utf-8', errors='ignore')
                
                if not text.strip():
                    logger.warning(f"antiword returned empty text for {doc_path}")
                    return []
                
                # Split into pages
                page_texts = re.split(r'\f|\n\s*\[\s*Page\s+\d+\s*\]', text)
                
                # Filter out empty pages
                page_texts = [page.strip() for page in page_texts if page.strip()]
                
                pages = []
                
                # Create page objects
                for i, page_text in enumerate(page_texts, 1):
                    pages.append(PageContent(
                        text=page_text,
                        page_number=i,
                        metadata={
                            "extraction_tool": "antiword"
                        }
                    ))
                
                # If no pages were split, create a single page
                if not pages and text.strip():
                    pages = [PageContent(
                        text=text.strip(),
                        page_number=1,
                        metadata={
                            "extraction_tool": "antiword",
                            "page_break_detection": "none"
                        }
                    )]
                
                return pages
                
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"antiword extraction failed: {str(e)}")
            raise
    
    def _extract_with_strings_cmd(self, doc_path: str) -> List[PageContent]:
        try:
            # Run the strings command
            result = subprocess.run(
                ["strings", doc_path],
                capture_output=True,
                check=True
            )
            
            text = result.stdout.decode('utf-8', errors='ignore')
            
            if not text.strip():
                logger.warning(f"strings command returned empty text for {doc_path}")
                return []
            
            # Clean up the text
            text = self._preprocess_text(text)
            
            # Create a single page
            return [PageContent(
                text=text,
                page_number=1,
                metadata={
                    "extraction_tool": "strings_command",
                    "last_resort": True
                }
            )]
            
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"strings command extraction failed: {str(e)}")
            raise
    
    def extract(self, file_path: str) -> List[PageContent]:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []
        
        # Detect file type regardless of extension
        detected_type = self._detect_file_type(file_path)
        logger.info(f"Detected file type for {file_path}: {detected_type}")
        
        # Extract based on detected type
        if "pdf" in detected_type.lower():
            return self.extract_from_pdf(file_path)
        elif any(doc_type in detected_type.lower() for doc_type in ["word", "docx", "doc", "openxmlformats", "msword"]):
            return self.extract_from_doc(file_path)
        else:
            # Try to extract based on file extension as fallback
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.pdf':
                return self.extract_from_pdf(file_path)
            elif file_ext in ('.docx', '.doc'):
                return self.extract_from_doc(file_path)
            else:
                logger.error(f"Unsupported file format: {detected_type} ({file_ext})")
                return []
    
    def extract_text_with_layout(self, file_path: str) -> List[PageContent]:
        # Detect file type regardless of extension
        detected_type = self._detect_file_type(file_path)
        
        # Extract based on detected type
        if "pdf" in detected_type.lower():
            return self._extract_pdf_with_layout(file_path)
        else:
            # For non-PDF files, use regular extraction
            return self.extract(file_path)
    
    @exception_handler
    def _extract_pdf_with_layout(self, pdf_path: str) -> List[PageContent]:
        pages = []
        
        # Ensure the file exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return pages
        
        # Extract PDF metadata
        pdf_metadata = self._extract_pdf_metadata(pdf_path)
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pdf_metadata['total_pages'] = total_pages
            
            for page_num in range(1, total_pages + 1):
                try:
                    page = pdf.pages[page_num - 1]
                    page_structure = self._get_page_structure_info(page)
                    
                    # Extract all elements with their positions
                    layout_elements = []
                    
                    # Extract text with coordinates
                    if hasattr(page, 'extract_words') and callable(page.extract_words):
                        words = page.extract_words()
                        for word in words:
                            layout_elements.append({
                                'type': 'word',
                                'text': word.get('text', ''),
                                'x0': word.get('x0'),
                                'y0': word.get('y0'),
                                'x1': word.get('x1'),
                                'y1': word.get('y1')
                            })
                    
                    # Extract images with coordinates
                    if hasattr(page, 'images') and page.images:
                        for i, img in enumerate(page.images):
                            layout_elements.append({
                                'type': 'image',
                                'index': i,
                                'x0': img.get('x0'),
                                'y0': img.get('y0'),
                                'x1': img.get('x1'),
                                'y1': img.get('y1')
                            })
                    
                    # Extract tables
                    if hasattr(page, 'find_tables') and callable(page.find_tables):
                        tables = page.find_tables()
                        for i, table in enumerate(tables):
                            rows = []
                            for row in table.extract():
                                rows.append([str(cell) if cell is not None else '' for cell in row])
                            
                            layout_elements.append({
                                'type': 'table',
                                'index': i,
                                'rows': rows,
                                'x0': table.bbox[0],
                                'y0': table.bbox[1],
                                'x1': table.bbox[2],
                                'y1': table.bbox[3]
                            })
                    
                    # Extract regular text content
                    text = page.extract_text() or ""
                    
                    # Check if we should use OCR
                    if self._should_use_ocr(text) or page_structure.get('likely_scanned', False):
                        with tempfile.TemporaryDirectory() as temp_dir:
                            # Convert page to image
                            images = convert_from_path(
                                pdf_path,
                                dpi=self.dpi,
                                first_page=page_num,
                                last_page=page_num
                            )
                            
                            if images:
                                temp_img_path = os.path.join(temp_dir, f"page_{page_num}.png")
                                images[0].save(temp_img_path)
                                
                                # Perform OCR
                                text = self._perform_ocr(temp_img_path)
                                page_structure['extraction_method'] = 'ocr'
                    else:
                        page_structure['extraction_method'] = 'pdfplumber'
                    
                    # Create page metadata with layout information
                    page_metadata = {
                        **pdf_metadata,
                        **page_structure,
                        "page_number": page_num,
                        "layout_elements": layout_elements
                    }
                    
                    # Add the extracted page content
                    pages.append(PageContent(
                        text=text.strip(),
                        page_number=page_num,
                        metadata=page_metadata
                    ))
                    
                except Exception as e:
                    logger.error(f"Error extracting layout for page {page_num}: {str(e)}")
                    
                    # Still add the page with basic extraction if layout extraction fails
                    try:
                        page = pdf.pages[page_num - 1]
                        text = page.extract_text() or ""
                        
                        pages.append(PageContent(
                            text=text.strip(),
                            page_number=page_num,
                            metadata={
                                **pdf_metadata,
                                "page_number": page_num,
                                "extraction_method": "fallback"
                            }
                        ))
                    except:
                        # If even basic extraction fails, add an empty page
                        pages.append(PageContent(
                            text="",
                            page_number=page_num,
                            metadata={
                                **pdf_metadata,
                                "page_number": page_num,
                                "extraction_failed": True
                            }
                        ))
        
        return pages


def save_to_json(pages: List[PageContent], output_path: str, include_metadata: bool = False):
    """
    Save extracted pages to JSON file.
    
    Args:
        pages (List[PageContent]): List of page contents
        output_path (str): Path to save the JSON file
        include_metadata (bool): Whether to include metadata in the output
    """
    if include_metadata:
        output = [{
            'text': p.text,
            'page_number': p.page_number,
            'metadata': p.metadata
        } for p in pages]
    else:
        output = [{
            'text': p.text,
            'page_number': p.page_number
        } for p in pages]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Example usage
    import glob
    extractor = DocumentExtractor(ocr_lang='eng')
    
    # Extract from documents
    for doc_path in glob.glob("/root/LLM-backend/Active IT Resumes/*.pdf"):
        doc_pages = extractor.extract(doc_path)
        print(f"Extracted {len(doc_pages)} pages from {doc_path}")
        for page_info in doc_pages:
            print(f"--- Page {page_info.page_number} ---")
            print(page_info.text[:100] + "..." if len(page_info.text) > 100 else page_info.text)
    
    # Save to JSON
    # save_to_json(doc_pages, "doc_output.json")