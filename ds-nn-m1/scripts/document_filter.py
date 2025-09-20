import magic
from pathlib import Path
from typing import Dict, List, Union
import os
from common.logs import logger
from common.s3_operations import S3Helper
from fastapi.responses import JSONResponse

class DocumentFilter:
    def __init__(self):
        self.mime = magic.Magic(mime=True)
        self.ALLOWED_MIMES = {
            'application/pdf',
            'application/msword',  # .doc
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'  # .docx
        }
        self.TMP_DIR = '/tmp/document_filter'
        if not os.path.exists(self.TMP_DIR):
            os.makedirs(self.TMP_DIR)

    # Define response structure as class attribute
    RESPONSE_FORMAT = {
        "success": {
            "message": str,
            "data": [
                {
                    "type": str,     # e.g., "External Links"
                    "value": [
                        {
                            "text": str,    # e.g., "Hyperlink"
                            "url": str,     # e.g., "https://..."
                            "page": str     # e.g., "24"
                        }
                    ]
                }
            ]
        },
        "error": {
            "message": str,
            "data": {}
        }
    }

    def create_response(self, success: bool, results: Union[Dict, None] = None) -> Dict:
        """
        Create standardized response following RESPONSE_FORMAT structure
        """
        if success:
            return {
                "message": "Document Format checked successfully.",
                "data": [
                    {
                        "type": "filtered_documents",
                        "value": [
                            {
                                "name": file['name']  # Changed from "text" to "name"
                            } for file in results['filtered']
                        ]
                    }
                ]
            }
        else:
            return {
                "message": f"Document Format check failed - {str(results) if results else 'Unknown error'}",
                "data": {}
            }

    def filter_documents(self, file_path: str) -> Dict:
        """
        Filter documents in a directory and return only filtered (non-allowed) files
        Args:
            file_path: Local path or S3 path (starting with 's3://')
        Returns:
            Dict with filtered files only
        """
        try:
            # Handle S3 paths
            if file_path.startswith('s3://'):
                file_path = self.download_s3_directory(file_path)
            
            dir_path = Path(file_path)
            
            if not dir_path.exists():
                raise FileNotFoundError(f"Directory {file_path} does not exist")
            
            logger.info(f"Scanning directory: {file_path}")
            
            results = {
                'filtered': []
            }
            
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    try:
                        file_mime = self.mime.from_file(str(file_path))
                        
                        file_info = {
                            'name': file_path.name,
                            'path': str(file_path),
                            'mime_type': file_mime
                        }
                        
                        if file_mime not in self.ALLOWED_MIMES:
                            results['filtered'].append(file_info)
                            logger.info(f"Filtered file found: {file_path.name}")
                            
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {str(e)}")
                        continue
            
            # Return only filtered documents
            return {
                "message": "Document Format checked successfully.",
                "data": [
                    {
                        "type": "filtered_documents",
                        "value": [
                            {
                                "name": file['name']
                            } for file in results['filtered']
                        ]
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in filter_documents: {str(e)}")
            return {
                "message": f"Document Format check failed - {str(e)}",
                "data": {}
            }

    def download_s3_directory(self, s3_path: str) -> str:
        """
        Downloads a directory from S3 to local temp directory
        Args:
            s3_path: S3 path in format 's3://bucket-name/path/to/directory'
        Returns:
            Local directory path where files were downloaded
        """
        try:
            parts = s3_path.replace('s3://', '').split('/')
            bucket_name = parts[0]
            prefix = '/'.join(parts[1:])
            
            local_dir = os.path.join(self.TMP_DIR, os.path.basename(prefix))
            os.makedirs(local_dir, exist_ok=True)
            
            s3_helper = S3Helper(bucket_name)
            s3_helper.download_directory(prefix, local_dir)
            
            logger.info(f"Successfully downloaded S3 directory to {local_dir}")
            return local_dir
            
        except Exception as e:
            logger.error(f"Error downloading S3 directory: {str(e)}")
            raise