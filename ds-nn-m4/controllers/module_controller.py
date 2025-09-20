from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from scripts.check_q_f_documents import DocFormatExtractor
from common.logs import logger

app = FastAPI()

class DocFormatCheck(BaseModel):
    document: str

@app.post('/check_q_f_docs')
async def check_q_f_document(request: DocFormatCheck):
    try:
        logger.info(str(f'Starting to check the format for document. ')+'[check_document_format] [controllers/module_controller.py:16]')

        document = request.document

        extractor = DocFormatExtractor()

        results = extractor.process_file(document)

        logger.info(str(f'Completed the check for format. ')+'[check_document_format] [controllers/module_controller.py:35]')

        return JSONResponse({
                "message": "Document Format checked successfully.",
                "data": {
                    "results": results
                }
            },
            status_code=200
        )

    except Exception as e:
        logger.error(str(f'{e}')+' [check_document_format] [controllers/module_controller.py:36]')
        raise Exception(str(f'{e}'))
