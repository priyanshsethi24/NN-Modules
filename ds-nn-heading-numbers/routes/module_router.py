from fastapi import APIRouter
from controllers.module_controller import check_document_format

router = APIRouter()

router.post("/check_heading_number")(check_document_format)