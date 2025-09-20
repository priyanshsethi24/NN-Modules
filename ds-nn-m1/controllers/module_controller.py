from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from scripts.document_filter import DocumentFilter
from common.logs import logger

class FilePath(BaseModel):
    file_path: str

async def filter_documents(request: FilePath):
    try:
        logger.info(f'Starting document filtering for path: {request.file_path}')
        
        document_filter = DocumentFilter()
        # Return the results directly without wrapping
        return document_filter.filter_documents(request.file_path)
        
    except Exception as e:
        logger.error(f'Error in filter_documents: {str(e)}')
        raise HTTPException(status_code=500, detail=str(e))