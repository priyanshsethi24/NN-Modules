# ds-nn-m2-yash_dev/ds-nn-m2-yash_dev/routes/module_router.py
from fastapi import APIRouter
from controllers.module_controller import filter_documents

router = APIRouter()

router.post("/filter_documents")(filter_documents)