import openai
import pytesseract
pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.analyze import router as analyze_router
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse

import os

import pytesseract
from PIL import Image
import io
from pdf2image import convert_from_bytes
import fitz  # PyMuPDF

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)

@app.post("/analyze-report")
async def analyze_report(file: UploadFile = File(...), mode: str = "simple"):
    content = await file.read()

    extracted_text = ""

    try:
        if file.filename.endswith(".pdf"):
            pdf = fitz.open(stream=content, filetype="pdf")
            for page in pdf:
                text = page.get_text("text")
                if text.strip():
                    extracted_text += text
                else:
                    try:
                        pix = page.get_pixmap()
                        img = Image.open(io.BytesIO(pix.tobytes("png")))
                        extracted_text += pytesseract.image_to_string(img)
                    except Exception:
                        continue
        else:
            # 🚫 Skip OCR (tesseract not installed)
            return JSONResponse({
                "summary": "📷 Image reports are not supported right now. Please upload a PDF report for accurate analysis."
            })

    except Exception as e:
        return JSONResponse({"summary": f"Error reading file: {str(e)}"})

    # Limit text length for now
    extracted_text = extracted_text[:1500]

    # 🔥 If no text extracted, do not stop, let AI try
    if not extracted_text.strip():
        extracted_text = "Report text could not be extracted clearly. It may be scanned. Try to infer possible medical insights cautiously."

    # 🔥 Auto-trigger advanced mode if user intent suggests detailed analysis
    advanced_keywords = ["detailed", "advanced", "full", "deep", "complete", "explain fully"]
    if any(keyword in extracted_text.lower() for keyword in advanced_keywords):
        mode = "advanced"

    # 🔥 Use AI for universal report understanding
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return JSONResponse({
            "summary": "⚠️ AI analysis not configured. Please set GROQ_API_KEY in environment. Showing raw report:\n\n" + extracted_text
        })

    client = Groq(api_key=api_key)

    try:
        if mode == "advanced":
            prompt = f"""
You are a medical report analyzer.

IMPORTANT RULES:
- Only use data present in the report text
- DO NOT invent values
- If unclear, say "unclear"

Tasks:
1. Summarize the report
2. Highlight abnormal values
3. Detect hidden patterns
4. Compare with typical cases
5. Explain why NOT serious
6. Mention risks
7. Predict future risks
8. Suggest doctor
9. Suggest precautions
10. Show uncertainty

Format:
Summary:
- ...

Abnormal Findings:
- ...

Hidden Pattern:
- ...

Case Comparison:
- ...

Why NOT Serious:
- ...

Possible Risks:
- ...

Future Risks:
- ...

Doctor Suggestion:
- ...

Precautions:
- ...

AI Confidence:
- ...

Uncertainty Note:
- ...

Report:
{extracted_text}
"""
        else:
            prompt = f"""
You are a medical report analyzer.

Tasks:
1. Give a short summary (2–3 lines)
2. Mention only key abnormal values
3. Detect one main pattern
4. Give simple risk insight
5. Suggest doctor
6. Keep everything concise

Format:
Summary:
- ...

Key Findings:
- ...

Main Pattern:
- ...

Risk Insight:
- ...

Doctor Suggestion:
- ...

Report:
{extracted_text}
"""

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        clean_output = completion.choices[0].message.content.strip()

        # remove duplicate heading if AI already added it
        if clean_output.lower().startswith("📊 report analysis"):
            clean_output = clean_output.split("\n", 1)[-1].strip()

        final_summary = "📊 Report Analysis:\n\n" + clean_output

    except Exception as e:
        print("AI ERROR:", str(e))
        final_summary = "⚠️ AI analysis failed. Showing raw report:\n\n" + extracted_text

    print("EXTRACTED TEXT:", extracted_text[:200])
    return JSONResponse({"summary": final_summary})


# Voice endpoint using OpenAI Whisper
@app.post("/voice")
async def voice_to_text(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()

        # Convert bytes to file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.webm"

        response = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )

        return {"text": response.text}

    except Exception as e:
        print("VOICE ERROR:", str(e))
        return {"text": ""}

@app.get("/")
def root():
    return {"message": "Medi AI Backend Running"}