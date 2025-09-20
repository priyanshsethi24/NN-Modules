from fastapi import APIRouter
from controllers.module_controller import check_document_format

router = APIRouter()

router.post("/check_bullet_points")(check_document_format)