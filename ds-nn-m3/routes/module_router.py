from fastapi import APIRouter
from controllers.module_controller import check_abbreviation

router = APIRouter()

router.post("/check_abbreviation")(check_abbreviation)