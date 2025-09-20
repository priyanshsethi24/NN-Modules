from common.logs import logger
from common.s3_operations import S3Helper
import os
from pathlib import Path
import time
import pythoncom
import win32com
from docx2pdf import convert
import subprocess

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

def download_s3_file(file_path: str) -> str:
        """
        Download a file from S3 using the provided file path.
        The file is downloaded to TMP_DIR with a unique timestamp appended.
        """
        try: # Ensure import is local
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
            local_doc_path = local_file_path  # Fix: Assign local_doc_path here
            logger.info("S3 file downloaded successfully: " + local_doc_path +
                        " [__init__ S3] [ds-nn-m9\\scripts\\template_extract.py:154]")
            return local_file_path
        except Exception as e:
                logger.error("Error downloading S3 file in __init__: " + str(e) +
                            " [__init__ S3-Error] [ds-nn-m9\\scripts\\template_extract.py:156]")
                raise Exception("Error downloading S3 file " + str(e)) 
        
def convert_to_pdf(file_path) -> str:
        """Convert document to PDF using Microsoft Office COM automation"""
        output_dir = os.path.dirname(file_path)
        pdf_file = os.path.join(output_dir, os.path.splitext(os.path.basename(file_path))[0] + '.pdf')
        try:
            try:
                pythoncom.CoInitialize()
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(file_path)
                doc.SaveAs(pdf_file, FileFormat=17)  # 17 represents PDF format
                return pdf_file
            except Exception as e:
                logger.error(f"COM automation failed: {str(e)}")
                try:
                    convert(file_path, pdf_file)
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
                                file_path
                            ]
                            subprocess.run(command, check=True)
                            return pdf_file
                    raise Exception("No viable PDF conversion method found")
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise Exception(f'{e}')
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

def convert_docx_to_pdf(file_path):
    try:
        if not file_path.endswith('docx'):
            raise Exception('File type not supported')

        if file_path.startswith('s3'):
            file_path = download_s3_file(file_path)

        pdf_path =  convert_to_pdf(file_path)
        file_name = os.path.basename(pdf_path)
        logger.info(str(f"New PDF with margin annotations saved as: {pdf_path}")+'[methodName] [scripts\margin_check.py:363]')
        logger.info(str('Uploading File to s3 ')+'[get_table_details] [scripts\sql_queries.py:136]')
        s3_helper.upload_file_to_s3(file_name=f'{TMP_DIR}/{file_name}', object_name=f'{file_name}')

        s3_path = f"s3://{bucket_name}/{file_name}"
        return s3_path
    except Exception as e:
        logger.error(str(f'Encountered the following error while converion - {e}')+' [convert_docx_to_pdf] [scripts\margin_check.py:120]')
        raise Exception(f'{e}')
