from pydantic import BaseModel

class SymptomInput(BaseModel):
    text: str