from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from scripts.margin_check import DocumentFormatReviewer, PDFFormatReviewer
from scripts.terminate_active_COM import terminate_active_processes
from common.logs import logger
from typing import Dict, Union

class DocFormatCheck(BaseModel):
    file_path: str
    margin_dict: Dict[str, Union[float, int]]

    @validator('margin_dict')
    def validate_margin_dict(cls, margin_dict):
        # Check if all margin keys are present
        required_margins = ['top', 'bottom', 'left', 'right']
        missing_margins = [margin for margin in required_margins if margin not in margin_dict]
        
        if missing_margins:
            raise ValueError(f"Missing margin values for: {', '.join(missing_margins)}")
        
        # Validate margin values
        for margin, value in margin_dict.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"Invalid margin value for {margin}: must be a non-negative number")
        
        return margin_dict

app = FastAPI()

@app.post('/check_margin')
async def check_margin(request: DocFormatCheck):
    try:
        logger.info(str(f'Starting to check the format for document. ')+'[check_document_format] [controllers/module_controller.py:16]')
        terminate_active_processes()
        document = request.file_path
        margin_dict = request.margin_dict
        
        if document.endswith('.docx'):
            reviewer = DocumentFormatReviewer(document, margin_dict)
            results = reviewer.review_document(margin_dict)
        elif document.endswith('.pdf'):
            reviewer = PDFFormatReviewer(document, margin_dict)
            results = reviewer.review_document()
        else:
            raise Exception("File type not supported.")
        
        logger.info(str(f'Completed the check for format. ')+'[check_document_format] [controllers/module_controller.py:35]')
        
        data = []
        for k, v in results.items():
            data.append({"type": k, "value": v})
        
        return JSONResponse({
            "message": "Document Format checked successfully.",
            "data": data,
            # "margins": margin_dict
        }, status_code= 200)
    
    except Exception as e:
        logger.error(str(f'{e}')+' [check_document_format] [controllers/module_controller.py:36]')
        return JSONResponse({
            "message": f"Document Format check failed - {str(e)}.",
            "data": []
        }, status_code=500)