import os
import time
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, Union

import pythoncom
import fitz  # PyMuPDF
import win32com.client
from docx import Document
from docx.shared import Inches, Twips, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx2pdf import convert
from PyPDF2 import PdfReader
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTAnno, LTTextBox
from lxml import etree

from common.logs import logger
from common.s3_operations import S3Helper

bucket_name = os.getenv('aws_bucket')
s3_helper = S3Helper(bucket_name)

def find_git_root(start_path: Path) -> Path:
    """Finds the root of the Git repository by looking for the .git folder."""
    current_path = start_path.resolve()
    while current_path != current_path.parent:  # Stop at the drive root (C:\, D:\, etc.)
        if (current_path / ".git").exists():
            return current_path
        current_path = current_path.parent  # Move up one level
    raise FileNotFoundError("Git repository root not found. Ensure the script is inside a Git repo.")


# Get the repo root (starting search from the script's location)
repo_root = find_git_root(Path(__file__).parent)
TMP_DIR = repo_root / "s3_downloads"
TMP_DIR.mkdir(parents=True, exist_ok=True)


class DocumentFormatReviewer:
    def __init__(self, doc_path: str, margin_dict: Dict[str, Union[float, int]]):
        """
        Initialize the DocumentFormatReviewer with a path to a Word document
        and a dictionary for margin specifications.
        """
        try:
            logger.info(f"Opening document: {doc_path}")
            # If the document is on S3, download it locally
            if doc_path.startswith('s3://'):
                doc_path = self.download_s3_file(doc_path)
            # self.document = Document(doc_path)
            self.file_path = doc_path
            self.margin_dict = margin_dict
            # self.heading_errors = []
            # self.margin_errors = []
            # self.bullet_errors = []
            logger.info("Document loaded successfully")
        except Exception as e:
            logger.error(f"Failed to open document: {str(e)}")
            raise Exception(f"Failed to open document: {str(e)}")

    def download_s3_file(self, file_path: str) -> str:
        """
        Download a file from S3 using the provided file path.
        The file is downloaded to TMP_DIR with a unique timestamp appended.
        """
        try:
            from common.s3_operations import S3Helper  # Ensure import is local
            s3_bucket = file_path.split('/')[2]
            s3_helper = S3Helper(s3_bucket)
            s3_key = '/'.join(file_path.split('/')[3:])
            ts = str(time.time()).replace('.', '_')
            local_key = list(s3_key.split('.'))
            local_key[0] += f'_{ts}'
            local_key = '.'.join(local_key)
            local_file_path = os.path.join(TMP_DIR, os.path.basename(local_key))
            logger.info("Downloading S3 file: " + file_path + " to local path: " + local_file_path +
                        " [__init__ S3] [ds-nn-m9\\scripts\\template_extract.py:150]")
            s3_helper.download_file_from_s3(s3_key, local_file_path)
            self.local_doc_path = local_file_path  # Fix: Assign local_doc_path here
            logger.info("S3 file downloaded successfully: " + self.local_doc_path +
                        " [__init__ S3] [ds-nn-m9\\scripts\\template_extract.py:154]")
            return local_file_path
        except Exception as e:
            logger.error("Error downloading S3 file in __init__: " + str(e) +
                         " [__init__ S3-Error] [ds-nn-m9\\scripts\\template_extract.py:156]")
            raise

    def convert_to_pdf(self) -> str:
        """Convert document to PDF using Microsoft Office COM automation"""
        output_dir = os.path.dirname(self.file_path)
        pdf_file = os.path.join(output_dir, os.path.splitext(os.path.basename(self.file_path))[0] + '.pdf')
        try:
            try:
                pythoncom.CoInitialize()
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(self.file_path)
                doc.SaveAs(pdf_file, FileFormat=17)  # 17 represents PDF format
                return pdf_file
            except Exception as e:
                logger.error(f"COM automation failed: {str(e)}")
                try:
                    convert(self.file_path, pdf_file)
                    return pdf_file
                except ImportError:
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
        finally:
            try:
                if doc:
                    doc.Close()
                    del doc
            except Exception as e:
                logger.error(str('Error deleting doc ') + '[convert to pdf] [scripts\\margin_check.py:137]')
            try:
                if word:
                    word.Quit()
                    del word
            except Exception as e:
                logger.error(str('Error deleting word app ') + '[convert to pdf] [scripts\\margin_check.py:143]')
            pythoncom.CoUninitialize()

    def preprocess_pdf_text(self, text):
        """
        Preprocesses PDF text to merge logical lines and handle formatting quirks.
        """
        lines = text.splitlines()
        processed_lines = []
        buffer_line = ""
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                if buffer_line:
                    processed_lines.append(buffer_line)
                    buffer_line = ""
                continue
            if buffer_line and not stripped_line[0].isupper() and not re.match(r'^\d+(\.\d+)*', stripped_line):
                buffer_line += f" {stripped_line}"
            else:
                if buffer_line:
                    processed_lines.append(buffer_line)
                buffer_line = stripped_line
        if buffer_line:
            processed_lines.append(buffer_line)
        return "\n".join(processed_lines)

    def check_page_margins(self, margin_dict: Dict[str, float]) -> List[str]:
        logger.info("Starting page margins check")
        try:
            pdf_path = self.convert_to_pdf()
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found at {pdf_path}")
            pdf_reviewer = PDFFormatReviewer(pdf_path, self.margin_dict)
            a, b = pdf_reviewer.check_page_margins()
            result = {
                'pdf_path': a,
                'page_numbers': b
            }
            return result
        except Exception as e:
            error_msg = f"Error in page margins check: {str(e)}"
            logger.error(error_msg)
            raise
        finally:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)

    def twips_to_inches(self, twips_obj) -> Optional[float]:
        """Convert a twips measurement to inches"""
        try:
            if hasattr(twips_obj, '_element'):
                twips = int(twips_obj._element.attrib.get('w:val', 0))
            else:
                twips = int(str(twips_obj))
            inches = twips / 1440.0
            return round(inches, 2)
        except (AttributeError, ValueError, TypeError) as e:
            logger.error(f"Error converting twips to inches: {str(e)}")
            return None

    def review_document(self, margin_dict: Dict[str, float]) -> Dict[str, List[str]]:
        logger.info("Starting complete document review")
        try:
            results = {
                'page_margins': self.check_page_margins(self.margin_dict)
            }
            total_errors = sum(len(issues) for issues in results.values())
            logger.info(f"Document review completed. Total errors found: {total_errors}")
            return results
        except Exception as e:
            error_msg = f"Failed to complete document review: {str(e)}"
            logger.error(error_msg)
            raise


class PDFFormatReviewer:
    def __init__(self, pdf_path: str, margin_dict: Dict[str, Union[float, int]]):
        """
        Initialize the PDFFormatReviewer with a path to a PDF document
        and a dictionary for margin specifications.
        """
        try:
            logger.info(f"Opening PDF: {pdf_path}")
            if pdf_path.startswith('s3://'):
                pdf_path = self.download_s3_file(pdf_path)
            # self.pdf_reader = PdfReader(pdf_path)
            # self.doc = fitz.open(pdf_path).
            self.pdf_path = os.path.normpath(os.path.abspath(pdf_path))
            self.margin_dict = margin_dict
            # logger.info(f"PDF loaded successfully. Total pages: {len(self.pdf_reader.pages)}")
        except Exception as e:
            logger.error(f"Failed to open PDF: {str(e)}")
            raise Exception(f"Failed to open PDF: {str(e)}")

    def download_s3_file(self, file_path: str) -> str:
        """
        Download a PDF from S3 using the provided file path.
        The file is downloaded to TMP_DIR with a unique timestamp appended.
        """
        try:
            from common.s3_operations import S3Helper
            s3_bucket = file_path.split('/')[2]
            s3_helper = S3Helper(s3_bucket)
            s3_key = '/'.join(file_path.split('/')[3:])
            ts = str(time.time()).replace('.', '_')
            local_key = list(s3_key.split('.'))
            local_key[0] += f'_{ts}'
            local_key = '.'.join(local_key)
            local_file_path = os.path.join(TMP_DIR, os.path.basename(local_key))
            logger.info("Downloading S3 file: " + file_path + " to local path: " + local_file_path +
                        " [__init__ S3] [ds-nn-m9\\scripts\\template_extract.py:150]")
            s3_helper.download_file_from_s3(s3_key, local_file_path)
            self.local_doc_path = local_file_path  # Fix: Assign local_doc_path here
            logger.info("S3 file downloaded successfully: " + self.local_doc_path +
                        " [__init__ S3] [ds-nn-m9\\scripts\\template_extract.py:154]")
            return local_file_path
        except Exception as e:
            logger.error("Error downloading S3 file in __init__: " + str(e) +
                         " [__init__ S3-Error] [ds-nn-m9\\scripts\\template_extract.py:156]")
            raise

    def check_page_margins(self):
        """
        Check page margins against provided margin dictionary

        Args:
            margin_dict (Dict[str, float]): Dictionary of expected margins

        Returns:
            List of pages with margin mismatches
        """
        logger.info("Starting page margins check")
        try:
            logger.info(str(f'PDF path - {self.pdf_path} ')+'[methodName] [scripts\margin_check.py:273]')
            doc = fitz.open(self.pdf_path)
            result = set()
            top_margin = self.margin_dict["top"]
            bottom_margin = self.margin_dict["bottom"]
            left_margin = self.margin_dict["left"]
            right_margin = self.margin_dict["right"]
            
            # Convert inches to points (1 inch = 72 points)
            n_top_margin = top_margin * 72
            n_bottom_margin = bottom_margin * 72
            n_left_margin = left_margin * 72
            n_right_margin = right_margin * 72


            for page_no in range(len(doc)):
                page = doc[page_no]
                page_rect = page.rect  # Get full page dimensions

                # Define a valid content area within margins
                valid_margin = fitz.Rect(
                    n_left_margin-5, 
                    n_top_margin-5, 
                    page_rect.width - n_right_margin + 5, 
                    page_rect.height - n_bottom_margin + 5
                )

                outside_items = []

                

                # 📝 Detect text outside the margin box
                for block in page.get_text("blocks"):
                    x0, y0, x1, y1, text, *_ = block
                    if (x0 < valid_margin.x0 or x1 > valid_margin.x1 or
                        y0 < valid_margin.y0 or y1 > valid_margin.y1) and text.strip():
                        # outside_items.append(ItemCoordinate(x0, y0, x1, y1, "Text", text=text))
                        result.add(page_no+1)
                        shape = page.new_shape()
                        logger.info(str(f'Block for {text} - {x0} {y0} {x1} {y1}')+'[methodName] [scripts\margin_check.py:322]')
                        shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
                        shape.finish(color=(1, 0, 0), width=0.5)  # Red box for text outside
                        shape.commit()

                # 🖼️ Detect images (figures) outside the margin box
                for img in page.get_images(full=True):
                    xref = img[0]
                    img_rects = page.get_image_rects(xref)
                    if not img_rects:
                        continue
                    img_rect = img_rects[0]
                    if img_rect.width < 15 or img_rect.height<15:
                        continue
                    x0, y0, x1, y1 = img_rect
                    if (x0 < valid_margin.x0 or x1 > valid_margin.x1 or
                        y0 < valid_margin.y0 or y1 > valid_margin.y1):
                        # outside_items.append(ItemCoordinate(x0, y0, x1, y1, "Figure"))
                        result.add(page_no+1)
                        shape = page.new_shape()
                        logger.info(str(f'{x0} {y0} {x1} {y1}')+'[methodName] [scripts\margin_check.py:322]')
                        shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
                        shape.finish(color=(1, 0, 0), width=0.5)  # Red box for images
                        shape.commit()

                # 📊 Detect tables (vector drawings) outside the margin box
                for drawing in page.get_drawings():
                    for path in drawing["items"]:
                        if path[0] == "re":  # Rectangle
                            if isinstance(path[1], fitz.Rect):  
                                rect = path[1]
                                x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                                if rect.width < 15 or rect.height<15:
                                    continue
                            elif len(path) == 5:
                                x0, y0, w, h = path[1:]
                                x1, y1 = x0 + w, y0 + h
                                if w < 15 or h < 15:
                                    continue
                            else:
                                continue

                            if (x0 < valid_margin.x0 or x1 > valid_margin.x1 or
                                y0 < valid_margin.y0 or y1 > valid_margin.y1):
                                # outside_items.append(ItemCoordinate(x0, y0, x1, y1, "Drawing"))
                                result.add(page_no+1)
                                shape = page.new_shape()
                                logger.info(str(f'{x0} {y0} {x1} {y1}')+' [methodName] [scripts\margin_check.py:322]')
                                shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
                                shape.finish(color=(1, 0, 0), width=0.5)  # Red box for drawings
                                shape.commit()
                
                logger.info(str(f'Drawing box for page - {page_no}')+ '[methodName] [scripts\margin_check.py:312]')
                logger.info(str(f'Top - {top_margin-5}\nBottom - {page_rect.height - bottom_margin + 5}\nLeft - {left_margin-5}\nRight - {page_rect.width - right_margin + 5}')+'[methodName] [scripts\margin_check.py:307]')
                # Draw valid margin as a blue box
                shape = page.new_shape()
                shape.draw_rect(valid_margin)
                shape.finish(color=(0, 0, 1), width=1.5)  # Blue box for valid margin
                shape.commit()

                # results.append(PageMargin(
                #     page_no=page_no + 1,
                #     page_height=page_rect.height,
                #     page_width=page_rect.width,
                #     valid_margin=valid_margin,
                #     outside_items=outside_items
                # ))

            # Save the modified PDF
            
            new_pdf_path = f"{TMP_DIR}/{os.path.basename(self.pdf_path).split('.')[0] + '_modified.pdf'}"
            new_pdf_path = os.path.normpath(os.path.abspath(new_pdf_path))
            print(new_pdf_path)
            doc.save(new_pdf_path)
            doc.close()

            file_name = os.path.basename(new_pdf_path)
            
            logger.info(str(f"New PDF with margin annotations saved as: {new_pdf_path}")+'[methodName] [scripts\margin_check.py:363]')
            logger.info(str('Uploading File to s3 ')+'[get_table_details] [scripts\sql_queries.py:136]')
            s3_helper.upload_file_to_s3(file_name=f'{TMP_DIR}/{file_name}', object_name=f'{file_name}')

            s3_path = f"s3://{bucket_name}/{file_name}"
            result_dict = []

            margins = { 
                "top":   top_margin, 
                "right":   right_margin, 
                "bottom": bottom_margin,
                "left": left_margin
            }
            result = list(result)
            for page_number in result:
                result_dict.append({"page_number": page_number, "expected_margins": margins})
            return s3_path, result_dict
        except Exception as e:
            logger.error(str(f'Encountered the following error while checking for margins - {e} ')+'[check_page_margins] [scripts\margin_check.py:365]')
            raise Exception(f'Encountered the following error while checking for margins - {e} ')



    def review_document(self) -> Dict[str, List[str]]:
        """Perform complete document format review"""
        logger.info("Starting complete PDF document review")
        try:
            a, b = self.check_page_margins()
            results = {
                'pdf_path': a,
                'page_numbers': b
            }
            res = {
                "page_margins": results
            }
            # total_errors = sum(len(issues) for issues in results.values())
            # logger.info(f"PDF document review completed. Total errors found: {total_errors}")
            return res
        except Exception as e:
            error_msg = f"Failed to complete PDF document review: {str(e)}"
            logger.error(error_msg)
            raise