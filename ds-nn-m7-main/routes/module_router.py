from fastapi import APIRouter
from controllers.module_controller import check_doc_bookmarks

router = APIRouter()

router.post("/check_bookmarks")(check_doc_bookmarks)