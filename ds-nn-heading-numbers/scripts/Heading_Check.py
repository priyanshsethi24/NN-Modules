from docx import Document
from docx.shared import Inches, Twips
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.shared import Pt
from typing import List, Dict, Tuple, Optional
from common.logs import logger
from common.s3_operations import S3Helper
import re, os
import tempfile
from PyPDF2 import PdfReader
from typing import List, Dict, Optional, Any
import re
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTAnno, LTTextBox
import fitz  # PyMuPDF
import subprocess
from lxml import etree
import win32com.client as win32

TMP_DIR = tempfile.gettempdir()

class DocumentFormatReviewer:
    def __init__(self, doc_path: str):
        """Initialize with path to Word document and logger"""
        try:
            logger.info(f"Opening document: {doc_path}")
            if doc_path.startswith('s3://'):
                doc_path = self.download_s3_file(doc_path)
            self.document = Document(doc_path)
            self.file_path = doc_path
            self.heading_errors = []
            self.margin_errors = []
            self.bullet_errors = []
            logger.info("Document loaded successfully")
        except Exception as e:
            logger.error(f"Failed to open document: {str(e)}")
            raise Exception(f"Failed to open document: {str(e)}")

    def download_s3_file(self, word_path):
        s3_bucket = word_path.split('/')[2]
        s3_helper = S3Helper(s3_bucket)
        s3_key = '/'.join(word_path.split('/')[3:])
        local_file_path = os.path.join(TMP_DIR, os.path.basename(s3_key))
        # Download the file from S3
        s3_helper.download_file_from_s3(s3_key, local_file_path)
        return local_file_path

    def convert_to_pdf(self) -> str:
        """Convert document to PDF using Microsoft Office COM automation"""
        output_dir = os.path.dirname(self.file_path)
        pdf_file = os.path.join(output_dir, os.path.splitext(os.path.basename(self.file_path))[0] + '.pdf')
        
        try:
            # Try using win32com for Word to PDF conversion
            try:
                import win32com.client
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(self.file_path)
                doc.SaveAs(pdf_file, FileFormat=17)  # 17 represents PDF format
                doc.Close()
                word.Quit()
                return pdf_file
            except Exception as e:
                logger.error(f"COM automation failed: {str(e)}")
                
                # Fallback to alternative conversion methods
                try:
                    # Try using docx2pdf if available
                    from docx2pdf import convert
                    convert(self.file_path, pdf_file)
                    return pdf_file
                except ImportError:
                    # Last resort: Try using system installed Office
                    soffice_paths = [
                        r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                        r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
                    ]
                    
                    for soffice_path in soffice_paths:
                        if os.path.exists(soffice_path):
                            command = [
                                soffice_path,
                                "/q",
                                "/n",
                                "/f",
                                "/c",
                                f"SaveAs.PDF({pdf_file})",
                                self.file_path
                            ]
                            subprocess.run(command, check=True)
                            return pdf_file
                    
                    raise Exception("No viable PDF conversion method found")
                    
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise

    def extract_word_headings(self) -> List:
        """Extract headings from Word document"""
        headings = []
        for para in self.document.paragraphs:
            if 'Heading' in para.style.name or 'Header' in para.style.name:
                if para.text.strip():
                    heading = (
                        para.text.strip(),
                        para.style.name
                    )
                    headings.append(heading)
        print(headings)
        return headings

    def preprocess_pdf_text(self,text):
        """
        Preprocesses PDF text to merge logical lines and handle formatting quirks.
        """
        lines = text.splitlines()
        processed_lines = []
        buffer_line = ""

        for line in lines:
            stripped_line = line.strip()

            if not stripped_line:  # Empty line, treat as a paragraph break
                if buffer_line:
                    processed_lines.append(buffer_line)
                    buffer_line = ""
                continue

            if buffer_line and not stripped_line[0].isupper() and not re.match(r'^\d+(\.\d+)*', stripped_line):
                buffer_line += f" {stripped_line}"
            else:
                if buffer_line:  # Add previous buffer to processed lines
                    processed_lines.append(buffer_line)
                buffer_line = stripped_line  # Start a new buffer

        if buffer_line:  # Add the last buffer line
            processed_lines.append(buffer_line)

        return "\n".join(processed_lines)

    def extract_heading_numbers_from_pdf(self, pdf_file: str, docx_headings: List) -> Dict[str, str]:
        """Extract heading numbers from PDF"""
        doc = None
        try:
            doc = fitz.open(pdf_file)
            full_text = ""
            for page in doc:
                full_text += page.get_text("text") + "\n"
            
            full_text = self.preprocess_pdf_text(full_text)
            print(full_text)
            matched_headings = {}
            for heading in docx_headings:
                if heading[0]:
                    heading_regex = re.escape(heading[0]).replace(r"\ ", r"\s*(?:\r?\n|\s)*")
                    # Create the combined pattern that matches the number and multi-line heading
                    combined_regex = rf"(?<!\S)\s*(\d+(?:\.\d+)*\.?)\s*(?:\r?\n|\s)*({heading_regex})"
                    print(combined_regex)
                    if re.search(combined_regex, full_text, re.DOTALL) is not None:
                        matches = re.findall(combined_regex, full_text,re.DOTALL)
                        if matches:
                            for match in matches:
                                # print('NUMBER')
                                print(match)
                                if match[0]:
                                    matched_headings[heading[0]] = match[0]
                                else:
                                    if not matched_headings.get(heading[0], None):
                                        matched_headings[heading[0]] = None
                                
                    else:
                        # print(2)
                        matched_headings[heading[0]] = None
                    # print(matched_headings[heading[0]])
                    print('---------------------------------------------')

            print(matched_headings)
            return matched_headings
        except Exception as e:
            logger.error(str(f'{e} ')+'[extract_heading_numbers_from_pdf] [scripts/format_checker.py:127]')
            raise Exception(f'{e}')

    def normalize_number(self, number: Optional[str]) -> Optional[Tuple[int, ...]]:
        """Normalize heading numbers for comparison"""
        if not number or number.strip() == '':
            return None
        number = number.strip().rstrip('.')
        try:
            parts = [part for part in number.split('.') if part]
            return tuple(map(int, parts))
        except (ValueError, AttributeError):
            return None

    def check_heading_hierarchy(self, heading_numbers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Validate heading hierarchy and numbering"""
        errors = []
        used_numbers = set()
        seen_prefixes = set()
        last_number_at_level = {}  # Track last number seen at each level with prefix
        max_section_seen = 0  # Track highest top-level section number
        sequence_broken = False  # Flag to track if a higher section number was seen
        
        # First pass: Check for missing and invalid numbers
        numbered_headings = []
        for heading_text, number in heading_numbers.items():
            if not number:
                errors.append({
                    "error_type": "Missing number",
                    "heading": heading_text,
                    "number": None,
                    "details": None
                })
                continue
                
            norm_number = self.normalize_number(number)
            if not norm_number:
                errors.append({
                    "error_type": "Invalid format",
                    "heading": heading_text,
                    "number": number,
                    "details": None
                })
            else:
                numbered_headings.append((heading_text, number, norm_number))
        
        # Check each heading
        for heading_text, number, norm_number in numbered_headings:
            # Check for reused numbers
            if norm_number in used_numbers:
                errors.append({
                    "error_type": "Number reuse",
                    "heading": heading_text,
                    "number": number,
                    "details": "Number already used"
                })
                continue
            used_numbers.add(norm_number)
            
            # Handle top-level sections
            if len(norm_number) == 1:
                if norm_number[0] > max_section_seen:
                    max_section_seen = norm_number[0]
                    sequence_broken = True
                elif norm_number[0] == max_section_seen:
                    errors.append({
                        "error_type": "Number reuse",
                        "heading": heading_text,
                        "number": number,
                        "details": "Section number already used"
                    })
            
            # Handle subsections
            else:
                current_level = len(norm_number)
                prefix = norm_number[:-1]
                current_num = norm_number[-1]
                
                # Check for incorrect sequences after higher section number
                if sequence_broken and norm_number[0] < max_section_seen:
                    errors.append({
                        "error_type": "Incorrect sequence",
                        "heading": heading_text,
                        "number": number,
                        "details": f"Cannot use section {norm_number[0]} after section {max_section_seen}"
                    })
                    continue
                
                # Check for missing parent sections
                for i in range(1, current_level):
                    intermediate_prefix = norm_number[:i]
                    if intermediate_prefix not in seen_prefixes:
                        errors.append({
                            "error_type": "Incorrect sequence",
                            "heading": heading_text,
                            "number": number,
                            "details": f"Missing parent section {'.'.join(map(str, intermediate_prefix))}"
                        })
                
                # Check sequence within level
                if prefix not in last_number_at_level:
                    # First number at this level should be 1
                    if current_num != 1:
                        errors.append({
                            "error_type": "Incorrect sequence",
                            "heading": heading_text,
                            "number": number,
                            "details": f"First number at this level should be 1"
                        })
                else:
                    # Check if number follows sequence
                    last_num = last_number_at_level[prefix]
                    if current_num != last_num + 1:
                        errors.append({
                            "error_type": "Incorrect sequence",
                            "heading": heading_text,
                            "number": number,
                            "details": f"Incorrect number sequence after {'.'.join(map(str, prefix))}.{last_num}"
                        })
                
                last_number_at_level[prefix] = current_num
            
            # Add all prefixes of current number to seen prefixes
            for i in range(1, len(norm_number) + 1):
                seen_prefixes.add(norm_number[:i])
        
        return errors

    def review_document_headings(self) -> List[str]:
        """Perform complete document review"""
        try:
            # if self.file_type == 'word':
                # Extract headings from Word
            docx_headings = self.extract_word_headings()
                
                # Convert to PDF and extract numbers
            pdf_file = self.convert_to_pdf()
            heading_numbers = self.extract_heading_numbers_from_pdf(pdf_file, docx_headings)
                
                # Check hierarchy
            errors = self.check_heading_hierarchy(heading_numbers)
            return errors
            # else:
            #     logger.error("PDF review not implemented")
            #     return ["PDF review not implemented"]
                
        except Exception as e:
            logger.error(f"Document review failed: {str(e)}")
            raise Exception(f'{e}')
    def review_document(self) -> Dict[str, List[str]]:
        logger.info("Starting complete document review")
        try:
            results = {
                'heading_numbering': self.review_document_headings(),
                # 'page_margins': self.check_page_margins(),
                # 'bullet_points': self.check_bullet_points()  # Added bullet point check
            }

            total_errors = sum(len(issues) for issues in results.values())
            logger.info(f"Document review completed. Total errors found: {total_errors}")
            return results

        except Exception as e:
            error_msg = f"Failed to complete document review: {str(e)}"
            logger.error(error_msg)
            raise

class PDFFormatReviewer:
    def __init__(self, pdf_path: str):
        """Initialize with path to PDF document and logger"""
        try:
            logger.info(f"Opening PDF: {pdf_path}")
            if pdf_path.startswith('s3://'):
                pdf_path = self.download_s3_file(pdf_path)
            self.pdf_reader = PdfReader(pdf_path)
            self.doc = fitz.open(pdf_path)  # PyMuPDF document
            logger.info(f"PDF loaded successfully. Total pages: {len(self.pdf_reader.pages)}")
        except Exception as e:
            logger.error(f"Failed to open PDF: {str(e)}")
            raise

    def download_s3_file(self, word_path):
        s3_bucket = word_path.split('/')[2]
        s3_helper = S3Helper(s3_bucket)
        s3_key = '/'.join(word_path.split('/')[3:])
        local_file_path = os.path.join(TMP_DIR, os.path.basename(s3_key))
        # Download the file from S3
        s3_helper.download_file_from_s3(s3_key, local_file_path)
        return local_file_path

    def get_heading_level(self, text: str, font_size: float) -> Optional[int]:
        """Determine heading level based on font size and formatting"""
        try:
            # Common heading patterns (e.g., "1.", "1.1", "1.1.1")
            heading_pattern = r'^\d+(\.\d+)*\s+'

            if re.match(heading_pattern, text):
                # Determine level based on number of dots + 1
                dots = text.split()[0].count('.')
                level = dots + 1
                logger.info(f"Detected heading level {level} for text: {text}")
                return level
            return None
        except Exception as e:
            logger.error(f"Error determining heading level: {str(e)}")
            return None

    def check_heading_numbering(self) -> List[str]:
        """Check if headings are numbered correctly and sequentially"""
        logger.info("Starting heading numbering check")
        errors = []
        current_levels = [0] * 9  # Track numbering for up to 9 levels

        try:
            for page_num, page in enumerate(self.doc, 1):
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span["text"].strip()
                                font_size = span["size"]

                                level = self.get_heading_level(text, font_size)
                                if level is not None:
                                    logger.info(f"Checking heading on page {page_num}: {text}")
                                    level -= 1  # Convert to 0-based index

                                    # Check if higher level headings exist
                                    for i in range(level):
                                        if current_levels[i] == 0:
                                            error_msg = f"Page {page_num}: Heading level {level + 1} found before level {i + 1}"
                                            logger.error(error_msg)
                                            errors.append(error_msg)
                                    
                                    # Update numbering
                                    current_levels[level] += 1
                                    for i in range(level + 1, 9):
                                        current_levels[i] = 0
                                    
                                    # Check numbering format
                                    expected_number = '.'.join(str(n) for n in current_levels[:level + 1] if n > 0)
                                    if not text.startswith(expected_number):
                                        error_msg = f"Page {page_num}: Incorrect heading numbering: '{text}' should start with '{expected_number}'"
                                        logger.error(error_msg)
                                        errors.append(error_msg)

        except Exception as e:
            error_msg = f"Error in heading numbering check: {str(e)}"
            logger.error(error_msg)
            raise

        logger.info(f"Completed heading numbering check. Found {len(errors)} errors")
        return errors
