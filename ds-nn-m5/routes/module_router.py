from fastapi import APIRouter
from controllers.module_controller import ModuleController
from typing import List, Dict, Any
from scripts.models import FormatIssue
from pydantic import BaseModel
from fastapi.responses import JSONResponse

class DocumentRequest(BaseModel):
    file_path: str

router = APIRouter()
controller = ModuleController()

@router.post("/check-format")
async def check_document_format(request: DocumentRequest):
    """
    Check the formatting of a document (PDF or DOCX) using file path
    """
    try:
        issues = await controller.check_document_format(request.file_path)
        
        response_dict = {
            "message": "Document Format checked successfully.",
            "data": []
        }

        if issues:
            # Group all formatting issues
            format_issues = {
                "type": "Format Errors",
                "value": []
            }

            # Style labels mapping
            style_labels = {
                'Heading 1': 'Level 1 Heading',
                'Heading 2': 'Level 2 Heading',
                'Heading 3': 'Level 3 Heading',
                'Normal': 'Body Text'
            }

            for issue in issues:
                format_issues["value"].append({
                    "text": issue.text,
                    "current": issue.current_size,
                    "expected": f"{issue.expected_size} ({style_labels[issue.style]})",
                    "page": str(issue.page)
                })
            
            if format_issues["value"]:
                response_dict["data"].append(format_issues)

        return JSONResponse(response_dict, status_code=200)
        
    except Exception as e:
        error_response = {
            "message": str(e),
            "data": {}
        }
        return JSONResponse(error_response, status_code=500)
