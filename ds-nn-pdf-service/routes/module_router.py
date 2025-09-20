from fastapi import APIRouter
from controllers.module_controller import convert_docx

router = APIRouter()

router.post("/convert_to_pdf")(convert_docx)