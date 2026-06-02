from fastapi import APIRouter
from models.symptom_model import SymptomInput
from services.ai_engine import analyze_with_ai

router = APIRouter()

@router.post("/analyze")
def analyze(input: SymptomInput):
    result = analyze_with_ai(input.text)
    return result