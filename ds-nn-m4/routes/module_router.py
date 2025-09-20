from fastapi import APIRouter
from controllers.module_controller import check_q_f_document

router = APIRouter()

router.post("/check_q_f_docs")(check_q_f_document)