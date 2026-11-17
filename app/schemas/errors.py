from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """404 ve 409 yanıtlarının gövdesi: {"detail": "..."}.

    HTTPException ve ConflictError handler'ı bu biçimde döner; model yalnızca
    OpenAPI'de belgelemek içindir.
    """

    detail: str


def error_response(description: str) -> dict:
    """Decorator'daki `responses=` için tek bir hata kodunun tanımı."""
    return {"model": ErrorResponse, "description": description}
