from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from scripts.conversion_pdf import convert_docx_to_pdf
from scripts.terminate_active_COM import terminate_active_processes
from common.logs import logger
from typing import Dict, Union

class DocFormatCheck(BaseModel):
    file_path: str

app = FastAPI()

@app.post('/convert_to_pdf')
async def convert_docx(request: DocFormatCheck):
    try:
        logger.info(str(f'Starting conversion ')+'[convert_docx] [controllers/module_controller.py:16]')
        terminate_active_processes()
        document = request.file_path
        
        if document.endswith('.docx'):
            path = convert_docx_to_pdf(document)
        else:
            raise Exception("File type not supported.")
        
        logger.info(str(f'Completed conversion')+'[convert_docx] [controllers/module_controller.py:35]')
        
        data = [{"type": "S3_Path", "value": path}]
        
        return JSONResponse({
            "message": "Document converted successfully.",
            "data": data,
        }, status_code= 200)
    
    except Exception as e:
        logger.error(str(f'{e}')+' [convert_docx] [controllers/module_controller.py:36]')
        return JSONResponse({
            "message": f"Document conversion failed - {str(e)}.",
            "data": []
        }, status_code=500)