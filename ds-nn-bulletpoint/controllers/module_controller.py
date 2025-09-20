from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from scripts.bullet_points_check import DocumentFormatReviewer
from common.logs import logger

app = FastAPI()

class DocFormatCheck(BaseModel):
    file_path: str

@app.post('/check_bullet_points')
async def check_document_format(request: DocFormatCheck):
    try:
        logger.info(str(f'Starting to check the format for document. ')+'[check_document_format] [controllers/module_controller.py:16]')

        document = request.file_path


        if document.endswith('.docx'):
            reviewer = DocumentFormatReviewer(document)

            results = reviewer.review_document()

        # elif document.endswith('.pdf'):
        #     reviewer = PDFFormatReviewer(document)

        #     results = reviewer.review_document()

        else:
            raise Exception("File type not supported.")

        logger.info(str(f'Completed the check for format. ')+'[check_document_format] [controllers/module_controller.py:35]')
        data = []
        for k, v in results.items():
            data.append({"type": k, "value": v})

        return JSONResponse({
                "message": "Document Format checked successfully.",
                "data": data
            },
            status_code=200
        )

    except Exception as e:
        logger.error(str(f'{e}')+' [check_document_format] [controllers/module_controller.py:36]')
        return JSONResponse({
                "message": f"Document Format check failed - str(f'{e}').",
                "data": []
            },
            status_code=500
        )