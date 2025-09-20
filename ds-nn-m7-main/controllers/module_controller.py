from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from scripts.validate_references import verify_references
from scripts.terminate_active_COM import terminate_active_processes
from common.logs import logger
import os
from common.s3_operations import S3Helper

TMP_DIR = '/tmp'
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

app = FastAPI()

class DocBookmarkCheck(BaseModel):
    file_path: str

@app.post('/check_bookmarks')
async def check_doc_bookmarks(request: DocBookmarkCheck):
    try:
        logger.info(str(f'Starting to check the format for document. ')+'[check_doc_bookmarks] [controllers/module_controller.py:16]')

        document = request.file_path
        terminate_active_processes()

        if document.endswith('.docx'):
            internal, toc = verify_references(document)

        else:
            raise Exception("File type not supported.")

        logger.info(str(f'Completed the check for bookmarks. ')+'[check_doc_bookmarks] [controllers/module_controller.py:35]')
        data = []
        # data.append({"type": "internal_links", "value": internal})
        # data.append({"type": "table_of_content", "value": toc})
        data.append({"type": "bookmark_errors", "value": internal+toc})


        return JSONResponse({
                "message": "Document Format checked successfully.",
                "data": data
            },
            status_code=200
        )

    except Exception as e:
        logger.error(str(f'{e}')+' [check_doc_bookmarks] [controllers/module_controller.py:36]')
        return JSONResponse({
                "message": f"Document Format check failed - str(f'{e}').",
                "data": []
            },
            status_code=500
        )