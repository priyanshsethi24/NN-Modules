import re
import docx
import pandas as pd
import pdfplumber
import os
from pathlib import Path
from common.logs import logger
from common.s3_operations import S3Helper
import os

TMP_DIR = '/tmp'
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

class DocFormatExtractor:
    def __init__(self):
        # Compile regex patterns for better performance
        self.q_pattern = re.compile(r'\[Q\d{6}\]')
        self.f_pattern = re.compile(r'F-\d{8}')
        
    def extract_from_docx(self, file_path):
        """Extract Q and F formats from DOCX files"""
        doc = docx.Document(file_path)
        text = ' '.join([paragraph.text for paragraph in doc.paragraphs])
        return self._find_matches(text)
    
    def extract_from_xlsx(self, file_path):
        """Extract Q and F formats from XLSX files"""
        df = pd.read_excel(file_path)
        # Convert all cells to string and concatenate
        text = ' '.join(df.astype(str).values.flatten())
        return self._find_matches(text)
    
    def extract_from_vsdx(self, file_path):
        """Extract Q and F formats from VSDX files"""
        # Since VSDX is essentially a ZIP file containing XML
        from zipfile import ZipFile
        import xml.etree.ElementTree as ET
        
        text = []
        with ZipFile(file_path) as visio:
            # Extract text from relevant XML files
            for item in visio.namelist():
                if item.startswith('visio/pages/'):
                    with visio.open(item) as page:
                        tree = ET.parse(page)
                        for elem in tree.iter():
                            if elem.text:
                                text.append(elem.text)
        
        return self._find_matches(' '.join(text))
    
    def extract_from_pdf(self, file_path):
        """Extract Q and F formats from PDF files"""
        text = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text())
        
        return self._find_matches(' '.join(text))
    
    def _find_matches(self, text):
        """Find all Q and F format matches in text"""
        q_matches = self.q_pattern.findall(text)
        f_matches = self.f_pattern.findall(text)
        
        return {
            'Q_formats': q_matches,
            'F_formats': f_matches
        }
    
    def process_file(self, file_path):
        """Process a single file based on its extension"""
        if file_path.startswith('s3://'):
            s3_bucket = file_path.split('/')[2]
            s3_helper = S3Helper(s3_bucket)
            s3_key = '/'.join(file_path.split('/')[3:])
            local_file_path = os.path.join(TMP_DIR, os.path.basename(s3_key))
                    # Download the file from S3
            s3_helper.download_file_from_s3(s3_key, local_file_path)
            file_path = local_file_path

        file_path = Path(file_path)
        extension = file_path.suffix.lower()

        
        try:
            if extension == '.docx':
                return self.extract_from_docx(file_path)
            elif extension == '.xlsx':
                return self.extract_from_xlsx(file_path)
            elif extension == '.vsdx':
                return self.extract_from_vsdx(file_path)
            elif extension == '.pdf':
                return self.extract_from_pdf(file_path)
            else:
                raise ValueError(f"Unsupported file format: {extension}")
        except Exception as e:
            return {'error': f"Error processing {file_path}: {str(e)}"}
    
    def process_directory(self, directory_path):
        """Process all supported files in a directory"""
        results = {}
        supported_extensions = {'.docx', '.xlsx', '.vsdx', '.pdf'}
        
        for file_path in Path(directory_path).rglob('*'):
            if file_path.suffix.lower() in supported_extensions:
                results[str(file_path)] = self.process_file(file_path)
        
        return results

# # Example usage
# if __name__ == "__main__":
#     extractor = DocFormatExtractor()
    
#     # Process a single file
#     result = extractor.process_file("/home/yash-stride/Downloads/Sample file1_eQUAL.docx")
#     print("Single file result:", result)
    
#     # Process an entire directory
#     results = extractor.process_directory("./documents")
#     print("\nDirectory results:")
#     for file_path, result in results.items():
#         print(f"\n{file_path}:")
#         print(result)