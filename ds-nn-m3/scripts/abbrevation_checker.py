import pandas as pd
import PyPDF2
import re
import csv
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict
from abc import ABC, abstractmethod
from common.logs import logger
from common.s3_operations import S3Helper
import os
TMP_DIR = '/tmp'
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)
# Set up logging


class DocumentReader(ABC):
    """Abstract base class for document readers"""
    @abstractmethod
    def read_content(self, file_path: str) -> str:
        """Read and return document content as string"""
        pass

class PDFReader(DocumentReader):
    """Concrete class for reading PDF documents"""
    def read_content(self, file_path: str) -> str:
        try:
            content = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    content.append(page.extract_text())
            return ' '.join(content)
        except Exception as e:
            logger.error(f"Error reading PDF file: {e}")
            raise

class DocxReader(DocumentReader):
    """Concrete class for reading DOCX documents"""
    def read_content(self, file_path: str) -> str:
        try:
            from docx import Document
            doc = Document(file_path)
            return ' '.join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error reading DOCX file: {e}")
            raise

class ReferenceLoader(ABC):
    """Abstract base class for loading reference data"""
    @abstractmethod
    def load_references(self, file_path: str) -> Dict[str, str]:
        """Load and return reference data as dictionary"""
        pass

class ExcelReferenceLoader(ReferenceLoader):
    """Concrete class for loading references from Excel"""
    def load_references(self, file_path: str) -> Dict[str, str]:
        try:
            df = pd.read_excel(file_path)
            return dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
        except Exception as e:
            logger.error(f"Error loading references from Excel: {e}")
            raise

class CSVReferenceLoader(ReferenceLoader):
    """Concrete class for loading references from CSV"""
    def load_references(self, file_path: str) -> Dict[str, str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                return {rows[0].strip(): rows[1].strip() 
                       for rows in csv_reader 
                       if len(rows) >= 2 and rows[0].strip() and rows[1].strip()}
        except Exception as e:
            logger.error(f"Error loading references from CSV: {e}")
            raise

class AbbreviationRepository:
    """Repository class for managing abbreviation data"""
    def __init__(self, reference_path: str):
        self.reference_path = reference_path
        self.loader = self._get_loader()
        self.abbreviations = self._load_abbreviations()

    def _get_loader(self) -> ReferenceLoader:
        """Get appropriate loader based on file extension"""
        file_ext = Path(self.reference_path).suffix.lower()
        if file_ext == '.xlsx':
            return ExcelReferenceLoader()
        elif file_ext == '.csv':
            return CSVReferenceLoader()
        else:
            raise ValueError(f"Unsupported reference file format: {file_ext}. Please use .xlsx or .csv")

    def _load_abbreviations(self) -> Dict[str, str]:
        """Load abbreviations using appropriate loader"""
        return self.loader.load_references(self.reference_path)

    def get_all_abbreviations(self) -> Dict[str, str]:
        return self.abbreviations

class AbbreviationAnalyzer:
    """Class for analyzing abbreviations in documents"""
    def __init__(self, abbreviation_repo: AbbreviationRepository):
        self.abbreviation_repo = abbreviation_repo

    def find_abbreviations_with_count(self, text: str) -> Dict[str, int]:
        """Find abbreviations with their occurrence counts"""
        abbr_counts = defaultdict(int)
        words = re.finditer(r'\b[A-Z]{2,}\b', text)
        for match in words:
            abbr = match.group()
            abbr_counts[abbr] += 1
        return dict(abbr_counts)

    def get_abbreviations_list(self, text: str) -> List[List[str]]:
        """Analyze document and return list of lists with abbreviation data"""
        abbr_counts = self.find_abbreviations_with_count(text)
        ref_abbrs = self.abbreviation_repo.get_all_abbreviations()
        
        # Initialize result with header
        result = [["Abbreviation", "Expanded Form", "Occurrences"]]
        
        # Add known abbreviations
        known_abbrs = [(abbr, count) for abbr, count in abbr_counts.items() if abbr in ref_abbrs]
        for abbr, count in sorted(known_abbrs):
            result.append([abbr, ref_abbrs[abbr], str(count)])
        
        # Add unknown abbreviations
        unknown_abbrs = [(abbr, count) for abbr, count in abbr_counts.items() if abbr not in ref_abbrs]
        if unknown_abbrs:
            result.append(["Unknown Abbreviations", "", ""])
            for abbr, count in sorted(unknown_abbrs):
                result.append([abbr, "Unknown", str(count)])
        
        return result

class DocumentProcessor:
    """Main processor class"""
    def __init__(self, analyzer: AbbreviationAnalyzer):
        self.analyzer = analyzer
        self.readers = {
            '.pdf': PDFReader(),
            '.docx': DocxReader(),
            '.doc': DocxReader()
        }

    def process_document(self, file_path: str) -> List[List[str]]:
        """Process document and return abbreviation data as list of lists"""
        file_path = Path(file_path)
        if file_path.suffix.lower() not in self.readers:
            raise ValueError(f"Unsupported file format: {file_path.suffix}. Please use PDF, DOCX, or DOC")

        reader = self.readers[file_path.suffix.lower()]
        content = reader.read_content(str(file_path))
        return self.analyzer.get_abbreviations_list(content)

def analyze_document_abbreviations(document_path: str, reference_path: str) -> List[List[str]]:
    """Main function to analyze document abbreviations and return results as list of lists"""
    try:
        if document_path.startswith('s3://'):
            s3_bucket = document_path.split('/')[2]
            s3_helper = S3Helper(s3_bucket)
            s3_key = '/'.join(document_path.split('/')[3:])
            local_file_path = os.path.join(TMP_DIR, os.path.basename(s3_key))
                    # Download the file from S3
            s3_helper.download_file_from_s3(s3_key, local_file_path)
            document_path = local_file_path
        
        if reference_path.startswith('s3://'):
            s3_bucket = reference_path.split('/')[2]
            s3_helper = S3Helper(s3_bucket)
            s3_key = '/'.join(reference_path.split('/')[3:])
            local_file_path = os.path.join(TMP_DIR, os.path.basename(s3_key))
                    # Download the file from S3
            s3_helper.download_file_from_s3(s3_key, local_file_path)
            reference_path = local_file_path

        abbreviation_repo = AbbreviationRepository(reference_path)
        analyzer = AbbreviationAnalyzer(abbreviation_repo)
        processor = DocumentProcessor(analyzer)
        return processor.process_document(document_path)
    
    except Exception as e:
        logger.error(f"Error analyzing document: {e}")
        raise

# def main():
#     """Example usage"""
#     # Can use either Excel or CSV for abbreviation references
#     reference_path = 'abbreviations.xlsx'  # or 'abbreviations.csv'
    
#     # Can process PDF, DOCX, or DOC files
#     document_path = 'sample_document.docx'
    
#     try:
#         result = analyze_document_abbreviations(document_path, reference_path)
        
#         # Print results in a formatted way
#         for row in result:
#             print(' | '.join(row))
            
#     except Exception as e:
#         logger.error(f"Error in main execution: {e}")
#         raise

# if __name__ == "__main__":
#     main()