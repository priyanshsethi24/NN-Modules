from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from contollers.module_controller import ModuleController
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from urllib.parse import urlparse

router = APIRouter()
controller = ModuleController()

class FilePathRequest(BaseModel):
    file_path: str

class ResultItem(BaseModel):
    type: str
    value: List[Dict[str, str]]

class SuccessResponse(BaseModel):
    message: str
    data: List[ResultItem]

class ErrorResponse(BaseModel):
    message: str
    data: dict

@router.post("/extract-links-from-path/")
async def extract_links_from_path(request: FilePathRequest):
    """
    Extract links from a file using its path
    Returns links with their details and page numbers
    """
    try:
        links = await controller.process_file_from_path(request.file_path)
        
        # Transform the links into dictionary format
        formatted_links = []
        for url, link_info in links.items():
            formatted_links.append({
                "text": link_info["display_text"],
                "url": url,
                "page": ", ".join(str(p) for p in link_info["pages"]) if link_info["pages"] else "Not Found"
            })

        # Create the response with a single type for external links
        response_data = [{
            "type": "External Links",
            "value": sorted(formatted_links, key=lambda x: x["text"])
        }]

        return JSONResponse(
            content={
                "message": "Document Format checked successfully.",
                "data": response_data
            },
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={
                "message": "Document Format check Failed.",
                "data": {}
            },
            status_code=500
        )
