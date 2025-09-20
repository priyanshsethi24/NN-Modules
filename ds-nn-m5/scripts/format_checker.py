import os
from .processors import DocumentProcessor
from .models import FormatIssue
from typing import List
from common.s3_operations import S3Operations

class FormatCheckerService:
    def __init__(self):
        self.processor = DocumentProcessor()
        self.s3_ops = S3Operations()
        self.tmp_dir = 'downloads'
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)

    async def check_document(self, file_path: str) -> List[FormatIssue]:
        try:
            local_path = file_path
            # Handle S3 files
            if file_path.startswith('s3://'):
                local_path = await self.download_s3_file(file_path)

            if not os.path.exists(local_path):
                raise ValueError(f"File not found: {local_path}")

            if local_path.lower().endswith('.docx'):
                issues = self.processor.process_docx(local_path)
            elif local_path.lower().endswith('.pdf'):
                issues = self.processor.process_pdf(local_path)
            else:
                raise ValueError("Unsupported file format. Please provide a .docx or .pdf file.")
            
            return issues
        except Exception as e:
            raise Exception(f"Error processing file: {str(e)}")

    async def download_s3_file(self, s3_path: str) -> str:
        """Download file from S3 and return local path"""
        try:
            filename = os.path.basename(s3_path)
            local_file_path = os.path.join(self.tmp_dir, filename)
            await self.s3_ops.download_file(s3_path, local_file_path)
            return local_file_path
        except Exception as e:
            raise Exception(f"Failed to download file from S3: {str(e)}")
