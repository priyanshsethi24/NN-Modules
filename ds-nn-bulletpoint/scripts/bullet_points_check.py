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

# Add the bullet configuration at the top level
EXPECTED_BULLETS = {
    1: ['•'],  # Level 1 - filled circle
    2: ['○', 'o'],  # Level 2 - hollow circle or 'o'
    3: ['▪', ''],  # Level 3 - filled square
}

# Define a mapping for bullet ASCII codes used in different fonts
BULLET_FONT_MAP = {
    'Wingdings': {
        8226: '•',  # Filled round bullet (•)
        8229: '▪',  # Filled square bullet (▪)
        10003: '✔',  # Check mark (✔)
        9675: '○',  # Hollow circle bullet (○)
    },
    'Symbol': {
        8226: '•',  # Filled round bullet (•)
        8229: '▪',  # Filled square bullet (▪)
        10003: '✔',  # Check mark (✔)
        9675: '○',  # Hollow circle bullet (○)
    },
    'Apis For Office': {
        61623: '•',  # Filled round bullet (•)
        61607: '',  # Square bullet ()
        61692: '',  # Checkmark ()
        111: 'o',  # Bullet symbol 'o' (o)
    }
}

# Use tempfile for cross-platform temporary directory
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

    def check_bullet_points(self) -> List[Dict[str, Any]]:
            """Check bullet point hierarchy and formatting"""
            logger.info("Starting bullet point check")
            word = None
            doc = None
            try:
                # Convert file path to absolute path with proper formatting
                abs_path = os.path.abspath(self.file_path)
                # Replace forward slashes with backslashes for Windows
                formatted_path = abs_path.replace('/', '\\')
                
                logger.info(f"Opening document for bullet point check: {formatted_path}")
                
                # Start Word application
                word = win32.Dispatch("Word.Application")
                word.Visible = False
                
                # Verify file exists before opening
                if not os.path.exists(formatted_path):
                    raise FileNotFoundError(f"Document not found at path: {formatted_path}")

                # Open the document
                doc = word.Documents.Open(formatted_path)
                bullet_points = []

                # Loop through each paragraph in the document
                for para in doc.Paragraphs:
                    # Check if the paragraph is part of a list (bullet point)
                    if para.Range.ListFormat.ListType == 2:  # ListType 2 means bullet points
                        # Get the bullet symbol and text
                        bullet_symbol = para.Range.ListFormat.ListString
                        text = para.Range.Text.strip()

                        # Get the font of the bullet
                        font_name = para.Range.Font.Name

                        # Get the level of the bullet (list level)
                        level = para.Range.ListFormat.ListLevelNumber

                        # Get the ASCII value of the bullet symbol
                        try:
                            ascii_value = ord(bullet_symbol)
                        except TypeError:
                            ascii_value = None

                        # Handle special font cases
                        if font_name in BULLET_FONT_MAP and ascii_value in BULLET_FONT_MAP[font_name]:
                            bullet_symbol_ascii = BULLET_FONT_MAP[font_name].get(ascii_value, bullet_symbol)
                        else:
                            bullet_symbol_ascii = bullet_symbol

                        # Check against expected symbols
                        expected_symbols = EXPECTED_BULLETS.get(level, [])
                        if bullet_symbol_ascii not in expected_symbols:
                            error_msg = {
                                "error_type": "Incorrect bullet symbol",
                                "page": '-',
                                "text": text,
                                "incorrect_symbol": f'{bullet_symbol_ascii} (ASCII: {ascii_value})',
                                "level": level,
                                "expected_symbol": f'{expected_symbols} (ASCII: {[ord(symbol) for symbol in expected_symbols if symbol]})'
                            }
                            bullet_points.append(error_msg)

                logger.info(f"Completed bullet point check. Found {len(bullet_points)} errors")
                return bullet_points

            except FileNotFoundError as e:
                logger.error(f"File not found error: {str(e)}")
                return [{"error_type": "File Error", "details": str(e)}]
            except Exception as e:
                error_msg = f"Error in bullet point check: {str(e)}"
                logger.error(error_msg)
                return [{"error_type": "System Error", "details": str(e)}]
            finally:
                # Ensure proper cleanup of Word objects
                try:
                    if doc:
                        doc.Close(SaveChanges=False)
                    if word:
                        word.Quit()
                except Exception as e:
                    logger.error(f"Error during Word cleanup: {str(e)}")

    def review_document(self) -> Dict[str, List[str]]:
        logger.info("Starting complete document review")
        try:
            results = {
                # 'heading_numbering': self.review_document_headings(),
                # 'page_margins': self.check_page_margins(),
                'bullet_points': self.check_bullet_points()  # Added bullet point check
            }

            total_errors = sum(len(issues) for issues in results.values())
            logger.info(f"Document review completed. Total errors found: {total_errors}")
            return results

        except Exception as e:
            error_msg = f"Failed to complete document review: {str(e)}"
            logger.error(error_msg)
            raise