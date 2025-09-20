from fastapi import APIRouter
from controllers.module_controller import check_margin

router = APIRouter()

router.post("/check_margin")(check_margin)