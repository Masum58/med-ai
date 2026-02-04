from fastapi import APIRouter

router = APIRouter()

@router.get(
    "",
    status_code=200,
    summary="Health check",
    description="Health check endpoint for Med-AI service"
)
def health_check():
    return {"status": "ok"}
