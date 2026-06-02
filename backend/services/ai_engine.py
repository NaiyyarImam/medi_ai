SESSION_MEMORY = {}
import os
from groq import Groq
from dotenv import load_dotenv
import json

# --- Emergency keywords ---
DANGER_KEYWORDS = [
    "heart attack", "stroke", "cancer", "tumor", "seizure", "unconscious",
    "vision loss", "temporary vision loss", "sudden blindness", "blurred vision sudden",
    "can't see", "loss of vision", "double vision",
    "chest tightness", "can't breathe", "difficulty breathing",
    "paralysis", "numbness one side", "face drooping",
    "severe bleeding", "vomiting blood", "blood in stool",
    "fainting", "blackout"
]

# --- Medicine info detection ---
MEDICINE_QUERY_KEYWORDS = [
    "what is", "use of", "purpose of", "why is", "function of"
]

# Common medicine names (expandable)
MEDICINE_NAMES = [
    "paracetamol", "ibuprofen", "aspirin", "crocin", "dolo", "azithromycin",
    "amoxicillin", "metformin", "omeprazole", "cetirizine", "pantoprazole"
]

# --- Research paper/research query detection ---
RESEARCH_KEYWORDS = [
    "research", "paper", "study", "journal", "review",
    "thesis", "analysis", "medical research"
]

def is_medicine_query(text):
    text_lower = text.lower()

    keyword_match = any(k in text_lower for k in MEDICINE_QUERY_KEYWORDS)
    medicine_name_match = any(med in text_lower for med in MEDICINE_NAMES)

    generic_words = ["tablet", "medicine", "drug", "capsule", "syrup", "bolus", "injection"]
    generic_match = any(word in text_lower for word in generic_words)

    # detect unknown drug-like words (important)
    suspicious = False

    return keyword_match or medicine_name_match or generic_match or suspicious

# --- AI-assisted probable medicine detection ---
def is_probable_medicine(text):
    """AI-assisted check for unknown medicine names"""
    try:
        prompt = f"""
        Determine if the following text refers to a medicine or drug.
        Answer ONLY yes or no.

        Text: {text}
        """

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        result = response.choices[0].message.content.lower()

        return "yes" in result
    except:
        return False

def handle_medicine_info(text):
    text_lower = text.lower()

    # 🚫 Detect dosage intent
    dosage_intent = any(word in text_lower for word in [
        "how many", "dosage", "dose", "mg", "tablet", "times", "per day",
        "can i take", "how much", "twice", "once", "3 times", "4 times"
    ])

    # 🚨 Detect possible overdose intent
    overdose_intent = any(word in text_lower for word in [
        "5", "6", "7", "8", "9", "10", "multiple", "many tablets",
        "at once", "together", "overdose", "extra dose"
    ]) and ("tablet" in text_lower or "mg" in text_lower or "dose" in text_lower)

    # 🚫 STRICT BLOCK: dosage queries
    if dosage_intent:
        return {
            "chat": "I can’t guide on dosage or how to take a medicine. That requires personalized medical judgment. Please consult a doctor or pharmacist for safe and accurate advice.",
            "title": f"About {text.split()[0].capitalize()}",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "medicine safety query",
                "part": {"display": "Body", "normalized": "body"},
                "confidence": 1.0,
                "severity": "medium",
                "specialist": "General Physician"
            }
        }

    # 🚨 OVERDOSE WARNING (high priority)
    if overdose_intent:
        return {
            "chat": "Taking a higher-than-recommended amount of a medicine can be dangerous and may lead to serious health risks, especially with pain relievers like paracetamol. It’s important not to exceed safe limits. If this has already happened, consider seeking medical help or contacting a healthcare professional immediately.",
            "title": f"About {text.split()[0].capitalize()}",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "possible overdose risk",
                "part": {"display": "Body", "normalized": "body"},
                "confidence": 1.0,
                "severity": "high",
                "specialist": "General Physician"
            }
        }

    prompt = f"""
You are a medical information assistant.

GOAL:
- Explain what the medicine is used for in simple, clear language
- Keep it informative but safe

STRICT RULES:
- Do NOT give dosage, timing, or how to take it
- Do NOT recommend using it
- Do NOT give prescriptions
- If user intent suggests usage → gently redirect to doctor
- Keep tone calm, helpful, and realistic (like ChatGPT)

OUTPUT STYLE:
- 2–3 short sentences
- Simple explanation of purpose
- One safety note if relevant

User input: {text}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        result = response.choices[0].message.content

        cleaned = result.strip()

        # Extra safety: remove suggestive phrases
        unsafe_phrases = [
            "you should take", "recommended to take", "you can take", "take this",
            "dosage", "mg", "tablet", "twice daily", "once daily",
            "per day", "every day", "every 6 hours", "3 times", "4 times"
        ]
        for phrase in unsafe_phrases:
            cleaned = cleaned.replace(phrase, "this is generally used for")

        return {
            "chat": cleaned,
            "title": f"About {text.split()[0].capitalize()}",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "medicine info",
                "part": {"display": "Body", "normalized": "body"},
                "confidence": 0.9,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    except Exception as e:
        print("Medicine Info Error:", e)
        return {
            "chat": "I can only provide general information about medicines. I am unable to safely analyze this request right now. Please consult a healthcare professional.",
            "title": f"About {text.split()[0].capitalize()}",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "medicine info",
                "part": {"display": "Body", "normalized": "body"},
                "confidence": 0.5,
                "severity": "low",
                "specialist": "General Physician"
            }
        }


# --- Research query handler ---
def handle_research_query(text):
    prompt = f"""
    You are a medical research assistant.

    TASK:
    - Understand the topic
    - Suggest 3–5 research directions
    - Mention possible methodologies
    - Suggest keywords for Google Scholar search

    Keep it structured and concise.

    User input: {text}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        result = response.choices[0].message.content.strip()

        return {
            "chat": result,
            "title": f"Research on {text[:25].strip().capitalize()}",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "research query",
                "part": {"display": "Body", "normalized": "body"},
                "confidence": 0.9,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    except Exception as e:
        print("Research Error:", e)
        return {
            "chat": "I can help guide your medical research. Try specifying the topic, for example: 'research on diabetes prediction using AI'.",
            "title": f"Research on {text[:25].strip().capitalize()}",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "research query",
                "part": {"display": "Body", "normalized": "body"},
                "confidence": 0.5,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

def map_to_3d(data):
    # (existing logic continues below)
    
    # --- SAFETY: ensure correct structure ---
    if not isinstance(data, dict):
        return {
            "chat": "Sorry, something went wrong while processing your request.",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "invalid response",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 0.3,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    # --- Ensure data is always dict ---
    if "data" not in data or not isinstance(data.get("data"), dict):
        data["data"] = {}

    # --- Ensure required nested structure ---
    data["data"].setdefault("organ", {"display": "Body", "normalized": "body"})
    data["data"].setdefault("part", {"display": "Muscle", "normalized": "muscle"})
    data["data"].setdefault("issue", "unknown")
    data["data"].setdefault("confidence", 0.5)
    data["data"].setdefault("severity", "low")
    data["data"].setdefault("specialist", "General Physician")

    valid_organs = ["head", "eye", "ear", "nose", "mouth", "neck", "shoulder", "arm", "hand", "chest", "abdomen", "back", "spine", "pelvis", "hip", "leg", "knee", "foot", "urinary", "body"]
    valid_parts = ["bone", "muscle", "nerve", "skin", "ligament"]

    try:
        organ_obj = data.get("data", {}).get("organ", {})
        organ = organ_obj.get("normalized", "") if isinstance(organ_obj, dict) else "body"
        part_obj = data.get("data", {}).get("part", {})
        part = part_obj.get("normalized", "muscle") if isinstance(part_obj, dict) else "muscle"
        issue_raw = data.get("data", {}).get("issue", "")
        issue = issue_raw.lower() if isinstance(issue_raw, str) else ""

        # --- Simplify issue for 3D consistency (not too basic, but controlled) ---
        if "anterior pelvic tilt" in issue or "pelvic tilt" in issue:
            issue = "lower back muscle imbalance"
        elif "l4" in issue or "lumbar" in issue:
            issue = "lower back strain"
        elif "sprain" in issue or "ligament" in issue:
            issue = "ligament strain"
        elif "nerve" in issue or "tingling" in issue or "radiating" in issue:
            issue = "nerve irritation"
        elif "fracture" in issue or "bone" in issue:
            issue = "bone injury"
        elif "inflammation" in issue:
            issue = "muscle inflammation"
        elif "posture" in issue:
            issue = "posture-related muscle strain"
        elif len(issue.split()) > 4:
            issue = issue.split()[0] + " issue"

        # Fix organ
        if organ not in valid_organs:
            organ = "body"

        # Special case: L4 / lumbar / lower back
        if "l4" in issue or "lumbar" in issue or "lower back" in issue:
            organ = "body"
            part = "muscle"

        # Special case: scapula / shoulder blade
        if "scapula" in issue or "shoulder blade" in issue:
            organ = "back"
            part = "muscle"

        # Special case: frequent urination / urinary issues
        if "urination" in issue or "urine" in issue or "toilet" in issue:
            organ = "urinary"
            part = "muscle"

        # Special case: brain / hypothalamus / neural system
        if "hypothalamus" in issue or "brain" in issue:
            organ = "head"
            part = "nerve"

        # Fix part consistency based on issue
        if "ligament" in issue:
            part = "ligament"
        elif "muscle" in issue or "strain" in issue:
            part = "muscle"
        elif "bone" in issue or "fracture" in issue:
            part = "bone"
        elif "nerve" in issue:
            part = "nerve"
        elif part not in valid_parts:
            part = "muscle"

        # Apply fixes
        data["data"]["issue"] = issue.capitalize()
        data["data"]["organ"]["normalized"] = organ
        data["data"]["organ"]["display"] = organ.capitalize()

        data["data"]["part"]["normalized"] = part
        data["data"]["part"]["display"] = part.capitalize()

    except Exception as e:
        print("Mapping Error:", e)

    # --- Confidence-aware chat adjustment ---
    try:
        confidence = data.get("data", {}).get("confidence", 0.5)
        chat = data.get("chat", "")

        if confidence < 0.5:
            chat = "It is not fully certain, but " + chat.lower()
        elif confidence > 0.8:
            chat = chat.replace("may be", "is likely").replace("maybe", "is likely")
            chat = chat.replace("could be", "is likely")

        data["chat"] = chat

    except Exception as e:
        print("Confidence Adjustment Error:", e)

    # --- Severity classification ---
    try:
        issue_raw = data.get("data", {}).get("issue", "")
        issue = issue_raw.lower() if isinstance(issue_raw, str) else ""
        if "fracture" in issue or "severe" in issue:
            severity = "high"
        elif "pain" in issue or "strain" in issue:
            severity = "medium"
        else:
            severity = "low"

        data["data"]["severity"] = severity
    except:
        data["data"]["severity"] = "low"

    # --- Specialist correction logic ---
    try:
        issue_raw = data.get("data", {}).get("issue", "")
        issue = issue_raw.lower() if isinstance(issue_raw, str) else ""
        organ_obj = data.get("data", {}).get("organ", {})
        organ = organ_obj.get("normalized", "") if isinstance(organ_obj, dict) else "body"

        if organ in ["knee", "leg", "arm", "shoulder", "hip", "back", "spine"] or any(word in issue for word in ["fracture", "sprain", "strain", "joint"]):
            specialist = "Orthopedic Specialist"

        elif organ in ["head", "brain"] or any(word in issue for word in ["nerve", "tingling", "numbness", "migraine"]):
            specialist = "Neurologist"

        elif "chest" in organ or any(word in issue for word in ["heart", "cardiac", "palpitation"]):
            specialist = "Cardiologist"

        elif organ in ["ear", "nose", "throat"] or any(word in issue for word in ["sinus", "hearing", "ear pain", "throat"]):
            specialist = "ENT Specialist"

        elif "eye" in organ or "vision" in issue:
            specialist = "Ophthalmologist"

        elif "urinary" in organ or "urine" in issue or "urination" in issue:
            specialist = "Urologist"

        elif any(word in issue for word in ["skin", "rash", "acne", "itching"]):
            specialist = "Dermatologist"

        else:
            specialist = "General Physician"

        data["data"]["specialist"] = specialist

    except Exception as e:
        print("Specialist Fix Error:", e)

    return data

# Load environment variables
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_with_ai(text: str, history=None, user_id="default", hinglish=False):
    # --- Input validation ---
    if not text or len(text.strip()) < 3:
        return {
            "chat": "Please describe your symptom more clearly.",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "invalid input",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 0.2,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    # --- Greeting / non-medical input handling ---
    text_lower = text.lower().strip()

    # --- Hinglish body-part normalization (IMPORTANT FIX) ---
    hindi_body_map = {
        "pet": "abdomen",
        "pait": "abdomen",
        "pet me": "abdomen",
        "pet mein": "abdomen",
        "pet mein dard": "abdomen pain",
        "sar": "head",
        "sir": "head",
        "gardan": "neck",
        "kamar": "back",
        "seena": "chest",
        "haath": "arm",
        "pair": "leg",
        "pairon": "leg",
        "ghutna": "knee",
        "aankh": "eye",
        "kaan": "ear"
    }

    for hindi_word, english_word in hindi_body_map.items():
        if hindi_word in text_lower:
            text = text.replace(hindi_word, english_word)
            text_lower = text.lower()
    # --- END normalization ---

    # --- Context-aware follow-up detection ---
    vague_followups = [
        "how can it be recovered", "how to recover", "how to treat",
        "what to do", "how to fix", "how to cure",
        "how to improve", "how can i improve", "how to manage",
        "recovery", "treatment"
    ]

    if any(phrase in text_lower for phrase in vague_followups):
        session_data = SESSION_MEMORY.get(user_id, {})
        last_issue = session_data.get("issue")
        last_organ = session_data.get("organ")

        if last_issue:
            if last_organ:
                text = f"treatment and recovery for {last_issue} in {last_organ}"
            else:
                text = f"treatment and recovery for {last_issue}"
            text_lower = text.lower()
        else:
            return {
                "chat": "To guide you properly, I need a bit more clarity about the condition you're referring to. Could you specify what symptom or issue you want to recover from?",
                "data": {
                    "organ": {"display": "Body", "normalized": "body"},
                    "issue": "unclear follow-up",
                    "part": {"display": "Muscle", "normalized": "muscle"},
                    "confidence": 0.5,
                    "severity": "low",
                    "specialist": "General Physician"
                }
            }

    # --- Detect explanation depth ---
    explanation_level = "basic"
    if any(word in text_lower for word in ["deep", "detail", "detailed", "explain deeply", "in depth"]):
        explanation_level = "advanced"
    elif any(word in text_lower for word in ["explain", "why", "how"]):
        explanation_level = "intermediate"

    # --- Detect advanced explanation intent ---
    risk_intent = any(word in text_lower for word in [
        "why", "cause", "causes", "how it happens", "reason",
        "what if", "if not treated", "risk", "danger", "complication"
    ])

    # --- Casual / general conversation handling ---
    if any(phrase in text_lower for phrase in [
        "how are you", "what's up", "wassup", "what are you doing",
        "who are you", "tell me about yourself"
    ]):
        return {
            "chat": "I'm Medi AI, here to help you understand health-related concerns and guide you safely. You can tell me about any symptom or ask general health questions.",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "general conversation",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 1.0,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    if any(phrase in text_lower for phrase in [
        "thanks", "thank you", "ok", "okay", "got it"
    ]):
        return {
            "chat": "You're welcome! If you have any other questions or symptoms you'd like to discuss, feel free to ask.",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "general conversation",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 1.0,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    if any(phrase in text_lower for phrase in [
        "bored", "nothing", "just chatting", "time pass"
    ]):
        return {
            "chat": "If you'd like, we can talk about health, fitness, or anything related to your well-being. Or you can describe any symptom you're experiencing.",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "general conversation",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 1.0,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    # --- Medicine query routing (enhanced) ---
    if is_medicine_query(text) or is_probable_medicine(text):
        return handle_medicine_info(text)

    # --- Research query routing ---
    if any(word in text_lower for word in RESEARCH_KEYWORDS):
        return handle_research_query(text)

    # --- Diagnostic Feature Extraction ---
    features = {
        "location": None,
        "duration": None,
        "trigger": None,
        "intensity": None
    }

    # location detection
    for part in ["head","neck","chest","back","abdomen","leg","knee","arm","eye","ear","shoulder","hip"]:
        if part in text_lower:
            features["location"] = part

    # duration detection (coarse)
    for word in ["hour","hours","day","days","week","weeks","month","months","year","years"]:
        if word in text_lower:
            features["duration"] = word

    # trigger detection
    for word in ["walking","running","lifting","eating","sleeping","sitting"]:
        if word in text_lower:
            features["trigger"] = word

    # intensity / quality
    for word in ["severe","mild","sharp","dull","heavy","burning","pressure","tightness"]:
        if word in text_lower:
            features["intensity"] = word

    # --- Initialize session memory (multi-user support) ---
    session = SESSION_MEMORY.get(user_id, {
        "organ": None,
        "issue": None,
        "duration": None,
        "severity": None,
        "history": []
    })
    session.setdefault("history", []).append(text)
    if len(session["history"]) > 5:
        session["history"] = session["history"][-5:]
    SESSION_MEMORY[user_id] = session

    if text_lower in ["hi", "hello", "hey", "marhaba", "salam", "namaste"]:
        return {
            "chat": "Hello! Please describe your health issue or symptom so I can help you better.",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "no medical issue",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 1.0,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    # --- Resolution / no-issue handling ---
    if any(phrase in text_lower for phrase in [
        "no issues", "now no issues", "problem solved", "i am fine", "feeling better", "all good", "issue fixed"
    ]):
        return {
            "chat": "That's great to hear! I'm glad you're feeling better. If anything comes up again or you need help in the future, feel free to ask.",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "resolved",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 1.0,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    # --- Reset context if user indicates new issue ---
    if any(word in text_lower for word in ["new problem", "another issue", "different issue", "new symptom"]):
        SESSION_MEMORY[user_id] = {
            "organ": None,
            "issue": None,
            "duration": None,
            "severity": None
        }

    # --- Time / duration input handling (context-aware follow-up) ---
    import re

    duration_patterns = [
        r"\b\d+\s*(hour|hours|hr|hrs)\b",
        r"\b\d+\s*(minute|minutes|min|mins)\b",
        r"\b\d+\s*(second|seconds|sec|secs)\b",
        r"\b\d+\s*(day|days)\b",
        r"\b\d+\s*(week|weeks)\b",
        r"\b\d+\s*(month|months)\b",
        r"\b\d+\s*(year|years)\b"
    ]

    if any(re.search(pattern, text_lower) for pattern in duration_patterns):
        session["duration"] = text
        SESSION_MEMORY[user_id] = session

        return {
            "chat": "Thanks for sharing the duration. Since this has been happening for some time, it helps narrow down whether it is temporary or persistent. I would also like to understand the intensity — is the discomfort mild, moderate, or severe?",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "duration context",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 0.8,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    # --- Advanced Emergency Detection (context + combination based) ---
    emergency = False

    # Strong direct keywords (always emergency)
    if any(word in text_lower for word in [
        "heart attack", "stroke", "seizure", "unconscious",
        "vision loss", "sudden blindness", "paralysis"
    ]):
        emergency = True

    # Chest pain + combined symptoms
    if "chest" in text_lower:
        if any(word in text_lower for word in ["pressure", "tightness"]):
            if any(word in text_lower for word in ["sweating", "nausea", "left arm", "jaw", "breath"]):
                emergency = True

    # Breathing critical
    if any(word in text_lower for word in ["can't breathe", "cannot breathe", "difficulty breathing", "shortness of breath severe"]):
        emergency = True

    # Neurological combos (stroke-like)
    if any(word in text_lower for word in ["face drooping", "slurred speech"]):
        emergency = True

    if "numbness" in text_lower:
        if "one side" in text_lower and not any(word in text_lower for word in ["sitting", "sleeping", "position", "long time"]):
            emergency = True

    if emergency:
        return {
            "chat": "⚠️ This combination of symptoms may indicate a serious or emergency condition (such as cardiac or neurological issues). Please seek immediate medical attention or go to the nearest hospital.",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "possible emergency condition",
                "part": {"display": "Organ", "normalized": "body"},
                "confidence": 0.9,
                "severity": "high",
                "specialist": "General Physician"
            }
        }

    # --- Rule-based override (high confidence cases) ---
    if "fracture" in text_lower or "broken bone" in text_lower:
        return {
            "chat": "It sounds like there may be a bone injury such as a fracture. This usually occurs due to trauma or excessive force and often requires proper medical evaluation. It would be advisable to avoid movement and support the affected area to prevent further injury. Have you experienced any swelling or difficulty moving the area?",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "bone injury",
                "part": {"display": "Bone", "normalized": "bone"},
                "confidence": 0.95,
                "severity": "high",
                "specialist": "Orthopedic Specialist"
            }
        }

    # --- Diagnostic Reasoning Engine (rule-first, context-aware) ---
    if features.get("location"):
        reasoning = []

        # Chest reasoning
        if features["location"] == "chest":
            reasoning.append("chest involvement")

            if features.get("trigger") in ["walking","running"]:
                reasoning.append("activity related")

            if features.get("intensity") in ["pressure","tightness"]:
                reasoning.append("pressure-type pain")

        # Limb / lower body reasoning
        if features["location"] in ["leg","knee","hip"]:
            if features.get("trigger") in ["walking","running","sitting"]:
                reasoning.append("movement related")

        # Decision rules
        if "chest involvement" in reasoning and "activity related" in reasoning and "pressure-type pain" not in reasoning:
            return {
                "chat": "Chest discomfort during activity can sometimes be related to muscle strain or exertion-related stress. It would help to understand if the sensation feels like pressure or tightness and whether it spreads to the arm or jaw. Could you describe the nature of the pain?",
                "data": {
                    "organ": {"display": "Chest", "normalized": "chest"},
                    "issue": "activity-related chest discomfort",
                    "part": {"display": "Muscle", "normalized": "muscle"},
                    "confidence": 0.75,
                    "severity": "medium",
                    "specialist": "General Physician"
                }
            }

        if "movement related" in reasoning:
            return {
                "chat": "The discomfort seems related to movement, which often suggests muscle fatigue or strain rather than a structural issue. This can happen due to overuse or posture-related stress. Does the discomfort improve after rest?",
                "data": {
                    "organ": {"display": "Leg", "normalized": "leg"},
                    "issue": "muscle strain",
                    "part": {"display": "Muscle", "normalized": "muscle"},
                    "confidence": 0.85,
                    "severity": "low",
                    "specialist": "Orthopedic Specialist"
                }
            }

    # --- Advanced reasoning upgrade ---
    if features.get("location") and features.get("intensity"):
        if features["location"] == "chest" and features["intensity"] in ["pressure", "tightness"]:
            return {
                "chat": "Chest pressure or tightness can indicate internal stress or strain. It is important to observe if it increases with activity or spreads. Avoid exertion and monitor closely. Does it worsen when walking or climbing stairs?",
                "data": {
                    "organ": {"display": "Chest", "normalized": "chest"},
                    "issue": "chest discomfort",
                    "part": {"display": "Muscle", "normalized": "muscle"},
                    "confidence": 0.85,
                    "severity": "medium",
                    "specialist": "General Physician"
                }
            }

        if features["location"] in ["leg", "thigh"] and features["intensity"] == "heavy":
            return {
                "chat": "A heavy feeling in the legs is often due to muscle fatigue or circulation strain. This can happen after prolonged activity or low conditioning. Rest and hydration can help. Does it improve after resting?",
                "data": {
                    "organ": {"display": "Leg", "normalized": "leg"},
                    "issue": "muscle fatigue",
                    "part": {"display": "Muscle", "normalized": "muscle"},
                    "confidence": 0.9,
                    "severity": "low",
                    "specialist": "Orthopedic Specialist"
                }
            }

    # --- State-aware flows for common issues ---

    # --- Body-part priority logic (prevents misclassification like weight → diet) ---
    if (any(word in text_lower for word in ["thigh", "leg", "knee", "calf"]) and any(word in text_lower for word in ["walking", "running", "sitting"])):
        return {
            "chat": "A feeling of heaviness in the legs or thighs during walking is often related to muscle fatigue or strain, especially if the muscles are overused or not conditioned. It may also be influenced by posture or prolonged activity. Rest and gentle stretching can help improve this. Does the heaviness reduce after resting?",
            "data": {
                "organ": {"display": "Leg", "normalized": "leg"},
                "issue": "muscle fatigue",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 0.85,
                "severity": "low",
                "specialist": "Orthopedic Specialist"
            }
        }

    # --- Nutrition / weight / calorie logic ---
    if any(word in text_lower for word in ["calorie", "kcal", "diet", "fat loss", "bulk", "cut"]):
        session["issue"] = "nutrition"
        SESSION_MEMORY[user_id] = session

        return {
            "chat": "Based on what you've shared, your diet and calorie intake may be influencing your current condition. A higher calorie intake than your body's requirement can lead to weight gain, while lower intake may cause fatigue or weakness. Maintaining a balanced intake based on your activity level is important. It would help to understand your routine better — are you aiming for weight loss, maintenance, or muscle gain?",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "diet imbalance",
                "part": {"display": "Body", "normalized": "body"},
                "confidence": 0.85,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    # Pain flow
    if "pain" in text_lower or "ache" in text_lower:
        if session.get("issue") == "pain":
            return {
                "chat": "Since you mentioned pain earlier, has the intensity changed (mild, moderate, or severe)? Does any movement make it worse?",
                "data": {
                    "organ": {"display": "Body", "normalized": "body"},
                    "issue": "pain",
                    "part": {"display": "Muscle", "normalized": "muscle"},
                    "confidence": 0.8,
                    "severity": session.get("severity") or "medium",
                    "specialist": "General Physician"
                }
            }

        session["issue"] = "pain"
        SESSION_MEMORY[user_id] = session

        return {
            "chat": "It seems like you're experiencing pain, which is often related to muscle strain or overuse. Resting the area and avoiding heavy movement can help, and applying heat or cold may reduce discomfort. Have you noticed if any specific activity triggers it?",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "pain",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 0.8,
                "severity": "medium",
                "specialist": "General Physician"
            }
        }

    # Fever flow
    if "fever" in text_lower or "temperature" in text_lower or "pyrexia" in text_lower:
        if session.get("issue") == "fever":
            return {
                "chat": "Since you're having a fever, is it continuous or coming and going? Do you have any other symptoms like cough or body aches?",
                "data": {
                    "organ": {"display": "Body", "normalized": "body"},
                    "issue": "fever",
                    "part": {"display": "Body", "normalized": "body"},
                    "confidence": 0.8,
                    "severity": session.get("severity") or "low",
                    "specialist": "General Physician"
                }
            }

        session["issue"] = "fever"
        SESSION_MEMORY[user_id] = session

        return {
            "chat": "A rise in body temperature is often the body's response to infection or inflammation. Rest, hydration, and avoiding exertion can help. Are you also experiencing symptoms like chills, cough, or body aches?",
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "fever",
                "part": {"display": "Body", "normalized": "body"},
                "confidence": 0.8,
                "severity": "low",
                "specialist": "General Physician"
            }
        }

    # Headache flow
    if "headache" in text_lower or ("head" in text_lower and "pain" in text_lower):
        if session.get("issue") == "headache":
            return {
                "chat": "Since the headache is still there, is it on one side or across the whole head? Does light or noise make it worse?",
                "data": {
                    "organ": {"display": "Head", "normalized": "head"},
                    "issue": "headache",
                    "part": {"display": "Nerve", "normalized": "nerve"},
                    "confidence": 0.8,
                    "severity": session.get("severity") or "medium",
                    "specialist": "Neurologist"
                }
            }

        session["issue"] = "headache"
        SESSION_MEMORY[user_id] = session

        return {
            "chat": "Headaches are often related to stress, fatigue, or tension. Rest, hydration, and reducing screen exposure may help. Do you feel the pain more on one side or all over the head?",
            "data": {
                "organ": {"display": "Head", "normalized": "head"},
                "issue": "headache",
                "part": {"display": "Nerve", "normalized": "nerve"},
                "confidence": 0.8,
                "severity": "medium",
                "specialist": "Neurologist"
            }
        }

    prompt = f"""
You are a medical assistant AI.

⚠️ STRICT RULE:
You MUST return ONLY VALID JSON.
NO extra text.
NO explanation outside JSON.
NO markdown (no ```json).
NO headings outside JSON.

If you do not follow JSON format, your response will be rejected.

REQUIRED FORMAT:

{{
  "chat": "your full structured answer",
  "data": {{
    "organ": {{
      "display": "Head",
      "normalized": "head"
    }},
    "issue": "short issue",
    "part": {{
      "display": "Muscle",
      "normalized": "muscle"
    }},
    "confidence": 0.8,
    "severity": "low",
    "specialist": "General Physician"
  }}
}}

Now follow all instructions below strictly.

    TASK:
    1. Understand the user's symptom clearly.
    2. Explain the most likely cause in simple medical terms.
    3. Provide a short list of 2–3 POSSIBLE CONDITIONS
       - Label them clearly as "Possible causes"
       - Keep them general and non-alarming
       - Do NOT present them as confirmed diagnoses
    4. ONLY IF user asks about causes or risks:
       - Explain briefly how the condition may have occurred
       - Mention possible risks if ignored (keep it non-alarming)
       - Keep it short and educational
    5. Provide safe, practical recovery guidance:
       - lifestyle changes
       - diet (if relevant)
       - rest / activity advice
       - hydration
       - when to seek medical help
    6. Ask a follow-up question ONLY if it adds value

    Only analyze COMMON and NON-CRITICAL issues.
    Do NOT diagnose serious diseases.

    IMPORTANT:
    - ALWAYS respond with BOTH:
      a) "chat" → professional explanation
      b) "data" → structured JSON

    JSON FORMAT (STRICT):

    {{
      "chat": "professional explanation ending with a follow-up question",
      "data": {{
        "organ": {{
          "display": "ONE of: Head, Eye, Ear, Nose, Mouth, Neck, Shoulder, Arm, Hand, Chest, Abdomen, Back, Spine, Pelvis, Hip, Leg, Knee Joint, Foot, Urinary System, Body",
          "normalized": "ONE of: head, eye, ear, nose, mouth, neck, shoulder, arm, hand, chest, abdomen, back, spine, pelvis, hip, leg, knee, foot, urinary, body"
        }},
        "issue": "short description",
        "part": {{
          "display": "ONE of: Bone, Muscle, Nerve, Skin, Ligament",
          "normalized": "ONE of: bone, muscle, nerve, skin, ligament"
        }},
        "confidence": 0.x,
        "severity": "low | medium | high",
        "specialist": "General Physician | Orthopedic Specialist | Neurologist"
      }}
    }}

    OUTPUT STYLE:
    - Response MUST be clearly structured using sections
    - Use simple headings like:
      • "Understanding the Issue"
      • "Possible Causes"
      • "What You Can Do"
      • "When to Seek Help"
    - Each section should be 1–2 short lines
    - Keep it clean, readable, and not too long
    - Avoid paragraphs — use line breaks

    RULES:
    - Always include BOTH chat and data
    - Chat MUST be helpful, natural, and:
      - Use line breaks between sections
      - Do NOT write long paragraphs
      - basic → 2–3 sentences
      - intermediate → 3–4 sentences
      - advanced → 4–6 sentences (include reasoning/mechanism)
    - Chat MUST follow this structured format:

      Understanding the Issue:
      - Brief explanation of what the symptom suggests

      Possible Causes:
      - List 2–3 possible causes (simple, non-alarming)

      What You Can Do:
      - Practical steps (rest, hydration, lifestyle, posture, etc.)

      When to Seek Help:
      - Mention when medical attention is needed

      OPTIONAL (only if user asks about causes/risks):
      - Add short explanation of why it happens or risks if ignored

    - ONLY IF the user asks about causes or risks, include a short explanation of why it may occur and what could happen if ignored (keep it non-alarming)
    - Ask a follow-up question ONLY when necessary
    - Do NOT ask repetitive or generic questions
    - If enough info is available, you may skip the question

    - Follow-up questions should be specific and contextual (not generic like "when did it start" repeatedly)
    - Prefer deeper questions like:
      • "Does it worsen with movement or rest?"
      • "Is the pain constant or coming in waves?"
    - Avoid repeating same question category (duration, severity, trigger)
    - If already asked, move to next logical step

    - Chat should sound professional but simple (not robotic)
    - Act as a cautious medical assistant
    - Do NOT give a confirmed diagnosis
    - You MAY provide 2–3 possible conditions, but clearly label them as possibilities
    - Never present them as final diagnosis
    - Avoid rare or extreme diseases unless strongly indicated
    - If the symptom is unclear, ask a short follow-up question inside the chat
    - Always provide safe, general guidance only
    - Avoid sounding overconfident
    - Use basic reasoning based on duration, intensity, and context if available
    - Do NOT repeat the same follow-up question if already answered earlier
    - If user provides numerical data (like calories, weight), interpret it logically before responding
    - Avoid giving empty or generic responses

    - At the end of chat, include a short disclaimer like:
      "This is general guidance and may not be fully accurate. Please consult a healthcare professional if needed."
    - Avoid vague phrases like "could be anything"
    - Do NOT mention multiple possible diagnoses using "or"
    - NEVER suggest multiple doctors in chat
    - Choose ONLY ONE most relevant specialist based on the primary symptom
    - Do NOT list options like "General Physician or Orthopedic" — pick one
    - Keep data simple and strictly mappable for 3D
    - "issue" MUST be a single, clear phrase (no "or", no combinations)
    - "specialist" MUST be only ONE from:
        General Physician | Orthopedic Specialist | Neurologist
    - Do NOT suggest medicines, drugs, or specific medical treatments
    - Do NOT return multiple answers
    - Do NOT return anything outside JSON
    - If you fail to follow JSON format, the response will be rejected
    - You MUST choose ONLY ONE value for organ and part (never multiple, never use "|")

    User input: {text}
    """

    try:
        # --- Build conversation history ---
        messages = []

        if history:
            for msg in history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # --- Explanation level control ---
        if explanation_level == "advanced":
            prompt += "\n\nADDITIONAL INSTRUCTION: Provide deeper explanation including physiological reasoning, mechanisms, and slightly more detailed causes. Keep it understandable but informative."
        elif explanation_level == "intermediate":
            prompt += "\n\nADDITIONAL INSTRUCTION: Provide a slightly more detailed explanation of causes and reasoning, but keep it simple and not too long."

        # --- Inject dynamic instruction if user asks about causes or risks ---
        if risk_intent:
            prompt += "\n\nADDITIONAL INSTRUCTION: The user is asking about causes or risks. Include a short explanation of why it may occur and what could happen if ignored."

        # --- Recovery intent boost ---
        if any(word in text_lower for word in ["recover", "recovery", "treat", "fix", "cure", "improve", "manage"]):
            prompt += "\n\nADDITIONAL INSTRUCTION: The user is asking about recovery or management. Provide clear, practical steps including diet (if relevant), hydration, lifestyle changes, activity modification, and when to seek medical help. Avoid vague advice. Be specific and realistic."

        # --- Always include main system prompt first ---
        messages.insert(0, {"role": "system", "content": prompt})

        # --- Hinglish enforcement (stronger) ---
        if hinglish:
            messages.insert(0, {
                "role": "system",
                "content": "You MUST respond ONLY in Hinglish (Hindi + English mix). Pure English is NOT allowed. Every sentence must include Hindi words like 'hai', 'ka', 'me', 'se'."
            })

        # --- Inject memory into prompt ---
        if session.get("issue"):
            messages.append({
                "role": "system",
                "content": f"Previous context: issue={session.get('issue')}, organ={session.get('organ')}, duration={session.get('duration')}, severity={session.get('severity')}"
            })

        # Add ONLY user input (not full prompt again)
        messages.append({"role": "user", "content": text})

        response = None
        for attempt in range(2):  # retry max 2 times
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                break
            except Exception as err:
                print(f"Retry {attempt+1} failed:", err)

        if not response:
            raise Exception("AI failed after retries")

        result = response.choices[0].message.content

        # --- FORCE JSON retry if model fails ---
        if not result.strip().startswith("{"):
            try:
                retry_messages = messages + [{
                    "role": "system",
                    "content": "RETURN ONLY VALID JSON. NO TEXT. NO MARKDOWN."
                }]

                retry_response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=retry_messages,
                    temperature=0
                )

                result = retry_response.choices[0].message.content
                print("RETRY JSON RESPONSE:", result)

            except Exception as retry_err:
                print("Retry JSON failed:", retry_err)

        # ❌ Prevent empty or useless responses
        if not result or len(result.strip()) < 20:
            raise Exception("Empty or weak AI response")

        print("GROQ RAW RESPONSE:", result)

        import re

        # Try to extract JSON inside ```json ``` block first
        json_block = re.search(r'```json\s*(\{.*\})\s*```', result, re.DOTALL)

        if json_block:
            try:
                parsed = json.loads(json_block.group(1))
                # --- Store memory from AI response ---
                try:
                    session["organ"] = parsed.get("data", {}).get("organ", {}).get("normalized")
                    session["issue"] = parsed.get("data", {}).get("issue")
                    session["severity"] = parsed.get("data", {}).get("severity")
                    SESSION_MEMORY[user_id] = session
                except:
                    pass
                # --- Improved follow-up memory (non-destructive) ---
                if "?" in parsed.get("chat", ""):
                    question = parsed["chat"].split("?")[-2].strip()

                    # Only store if new
                    if session.get("last_question") != question:
                        session["last_question"] = question
                        SESSION_MEMORY[user_id] = session
                    else:
                        # remove repeated question naturally
                        parsed["chat"] = parsed["chat"].rsplit("?", 1)[0] + "."
                # --- Validation check ---
                if (
                    "data" not in parsed or
                    "organ" not in parsed["data"] or
                    "part" not in parsed["data"] or
                    "issue" not in parsed["data"]
                ):
                    raise Exception("Invalid AI response structure")
                # --- Confidence fallback ---
                if "confidence" not in parsed.get("data", {}):
                    parsed["data"]["confidence"] = 0.6
                # --- SAFETY: ensure organ/part objects exist before mapping ---
                parsed.setdefault("data", {})
                parsed["data"].setdefault("organ", {"display": "Body", "normalized": "body"})
                parsed["data"].setdefault("part", {"display": "Muscle", "normalized": "muscle"})
                # --- Enforce single specialist consistency ---
                try:
                    specialist = parsed.get("data", {}).get("specialist", "")

                    # If AI gives confusing/general answer, fix it
                    if "or" in specialist.lower() or "," in specialist:
                        organ = parsed.get("data", {}).get("organ", {}).get("normalized", "")

                        if organ in ["knee","leg","arm","shoulder","hip","back","spine"]:
                            parsed["data"]["specialist"] = "Orthopedic Specialist"
                        elif organ in ["head"]:
                            parsed["data"]["specialist"] = "Neurologist"
                        else:
                            parsed["data"]["specialist"] = "General Physician"
                except:
                    pass
                # --- Ensure possible causes are labeled safely ---
                try:
                    chat_text = parsed.get("chat", "")
                    if "possible causes" not in chat_text.lower():
                        # avoid forcing, but ensure not misleading
                        pass
                except:
                    pass
                result = map_to_3d(parsed)

                # --- SIMPLE HINGLISH PLACEHOLDER (PRESENTATION ONLY) ---
                if hinglish:
                    try:
                        original = result.get("chat", "")
                        result["chat"] = f"(Hinglish Mode)\n\n{original}"
                    except Exception as e:
                        print("Hinglish placeholder failed:", e)

                # Generate smarter contextual title (based on user input + issue)
                try:
                    data_block = result.get("data", {})
                    issue = data_block.get("issue", "").strip().lower()
                    organ = data_block.get("organ", {}).get("display", "")

                    # Use original user text for better titles
                    user_text = text.strip().lower()

                    # Clean user text (short meaningful title)
                    if len(user_text) > 40:
                        user_text = user_text[:40].strip()

                    # Priority 1: meaningful issue
                    if issue and issue not in ["unknown", "unclear symptom", "general conversation"]:
                        if organ and organ.lower() != "body":
                            result["title"] = f"{organ} {issue.title()}"
                        else:
                            result["title"] = issue.title()

                    # Priority 2: fallback to user input
                    elif user_text:
                        result["title"] = user_text.capitalize()

                    # Final fallback
                    else:
                        result["title"] = "Health Consultation"

                except:
                    result["title"] = "Health Consultation"

                # --- Prevent repetitive titles ---
                try:
                    session_titles = SESSION_MEMORY.get(user_id, {}).get("titles", [])

                    if "title" in result:
                        current_title = result["title"]

                        # If same title repeated, slightly modify
                        if current_title in session_titles:
                            result["title"] = current_title + " (follow-up)"

                        session_titles.append(result["title"])
                        SESSION_MEMORY[user_id]["titles"] = session_titles[-10:]
                except:
                    pass

                return result
            except:
                pass

        # Fallback: extract largest JSON object
        json_match = re.search(r'\{[\s\S]*\}', result)

        if json_match:
            try:
                parsed = json.loads(json_match.group())
                # --- Store memory from AI response ---
                try:
                    session["organ"] = parsed.get("data", {}).get("organ", {}).get("normalized")
                    session["issue"] = parsed.get("data", {}).get("issue")
                    session["severity"] = parsed.get("data", {}).get("severity")
                    SESSION_MEMORY[user_id] = session
                except:
                    pass
                # --- Improved follow-up memory (non-destructive) ---
                if "?" in parsed.get("chat", ""):
                    question = parsed["chat"].split("?")[-2].strip()

                    # Only store if new
                    if session.get("last_question") != question:
                        session["last_question"] = question
                        SESSION_MEMORY[user_id] = session
                    else:
                        # remove repeated question naturally
                        parsed["chat"] = parsed["chat"].rsplit("?", 1)[0] + "."
                # --- Validation check ---
                if (
                    "data" not in parsed or
                    "organ" not in parsed["data"] or
                    "part" not in parsed["data"] or
                    "issue" not in parsed["data"]
                ):
                    raise Exception("Invalid AI response structure")
                # --- Confidence fallback ---
                if "confidence" not in parsed.get("data", {}):
                    parsed["data"]["confidence"] = 0.6
                # --- SAFETY: ensure organ/part objects exist before mapping ---
                parsed.setdefault("data", {})
                parsed["data"].setdefault("organ", {"display": "Body", "normalized": "body"})
                parsed["data"].setdefault("part", {"display": "Muscle", "normalized": "muscle"})
                # --- Enforce single specialist consistency ---
                try:
                    specialist = parsed.get("data", {}).get("specialist", "")

                    # If AI gives confusing/general answer, fix it
                    if "or" in specialist.lower() or "," in specialist:
                        organ = parsed.get("data", {}).get("organ", {}).get("normalized", "")

                        if organ in ["knee","leg","arm","shoulder","hip","back","spine"]:
                            parsed["data"]["specialist"] = "Orthopedic Specialist"
                        elif organ in ["head"]:
                            parsed["data"]["specialist"] = "Neurologist"
                        else:
                            parsed["data"]["specialist"] = "General Physician"
                except:
                    pass
                # --- Ensure possible causes are labeled safely ---
                try:
                    chat_text = parsed.get("chat", "")
                    if "possible causes" not in chat_text.lower():
                        # avoid forcing, but ensure not misleading
                        pass
                except:
                    pass
                result = map_to_3d(parsed)

                # --- SIMPLE HINGLISH PLACEHOLDER (PRESENTATION ONLY) ---
                if hinglish:
                    try:
                        original = result.get("chat", "")
                        result["chat"] = f"(Hinglish Mode)\n\n{original}"
                    except Exception as e:
                        print("Hinglish placeholder failed:", e)

                # Generate smarter contextual title (based on user input + issue)
                try:
                    data_block = result.get("data", {})
                    issue = data_block.get("issue", "").strip().lower()
                    organ = data_block.get("organ", {}).get("display", "")

                    # Use original user text for better titles
                    user_text = text.strip().lower()

                    # Clean user text (short meaningful title)
                    if len(user_text) > 40:
                        user_text = user_text[:40].strip()

                    # Priority 1: meaningful issue
                    if issue and issue not in ["unknown", "unclear symptom", "general conversation"]:
                        if organ and organ.lower() != "body":
                            result["title"] = f"{organ} {issue.title()}"
                        else:
                            result["title"] = issue.title()

                    # Priority 2: fallback to user input
                    elif user_text:
                        result["title"] = user_text.capitalize()

                    # Final fallback
                    else:
                        result["title"] = "Health Consultation"

                except:
                    result["title"] = "Health Consultation"

                # --- Prevent repetitive titles ---
                try:
                    session_titles = SESSION_MEMORY.get(user_id, {}).get("titles", [])

                    if "title" in result:
                        current_title = result["title"]

                        # If same title repeated, slightly modify
                        if current_title in session_titles:
                            result["title"] = current_title + " (follow-up)"

                        session_titles.append(result["title"])
                        SESSION_MEMORY[user_id]["titles"] = session_titles[-10:]
                except:
                    pass

                return result
            except:
                pass

        raise Exception("No valid JSON parsed")

    except Exception as e:
        print("Groq Error:", e)

        fallback_chat = "I couldn't fully understand the context of your question. If you're asking about recovery or treatment, please mention the specific condition or symptom so I can guide you more accurately."

        # 🔥 FORCE Hinglish fallback
        if hinglish:
            fallback_chat = "Mujhe aapka question properly samajh nahi aaya hai. Agar aap recovery ya treatment ke baare me puch rahe ho, toh please apna symptom thoda clearly bataye."

        return {
            "chat": fallback_chat,
            "data": {
                "organ": {"display": "Body", "normalized": "body"},
                "issue": "unclear symptom",
                "part": {"display": "Muscle", "normalized": "muscle"},
                "confidence": 0.3,
                "severity": "low",
                "specialist": "General Physician"
            }
        }