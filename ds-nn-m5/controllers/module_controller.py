from fastapi import HTTPException
from scripts.format_checker import FormatCheckerService
from typing import List
from scripts.models import FormatIssue

class ModuleController:
    def __init__(self):
        self.format_checker = FormatCheckerService()

    async def check_document_format(self, file_path: str) -> List[FormatIssue]:
        try:
            issues = await self.format_checker.check_document(file_path)
            return issues
        except ValueError as e:
            raise HTTPException(status_code=400, detail={
                "message": f"Invalid request: {str(e)}",
                "data": {}
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail={
                "message": f"Error processing document: {str(e)}",
                "data": {}
            })
