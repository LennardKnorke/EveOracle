from fastapi import APIRouter

router = APIRouter(
    prefix="/user",
)

@router.get("/me")
def get_me():
    return {"message": "Login"}

