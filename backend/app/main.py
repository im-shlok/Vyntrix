import os
import shutil
import json
import hashlib
import datetime
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from gtts import gTTS
from dotenv import load_dotenv
import speech_recognition as sr
from pydub import AudioSegment
from openai import OpenAI
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import cv2
import numpy as np
try:
    import torch
    from ultralytics import YOLO
except ImportError:
    torch = None
    YOLO = None
import re
from typing import Dict, Any, Optional

from app.core.database import (
    init_db,
    SessionLocal,
    LocationCache,
    AgentOutputCache,
    TelemetrySnapshot
)
from app.core.redis_client import redis_client
from app.agents.knowledge import seed_qdrant_knowledge
from app.agents.graph import compiled_graph
from app.agents.state import AgentState
from app.mcp.mcp_server import mcp_router
from app.core.seed_data import MANDI_PRICES

load_dotenv()  # Load environment variables from .env file
app = FastAPI(title="Agriva API", description="AI Operating System for Rural India backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static directory setup
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
VOICE_DIR = os.path.join(STATIC_DIR, "voice")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "agents",
    "models",
    "best.pt",
)
VISION_DEVICE = 0 if torch is not None and torch.cuda.is_available() else "cpu"
vision_model: Optional[Any] = None
os.makedirs(VOICE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount MCP Router
app.include_router(mcp_router)

# Server startup seeding pipeline
@app.on_event("startup")
def on_startup():
    print("[Startup] Initializing persistent SQLAlchemy tables...")
    init_db()
    global vision_model
    if YOLO is None:
        print("[Startup] Vision dependencies are unavailable; install backend requirements.")
    elif not os.path.isfile(MODEL_PATH):
        print(f"[Startup] Vision model not found: {MODEL_PATH}")
    else:
        try:
            vision_model = YOLO(MODEL_PATH)
            print(f"[Startup] YOLO vision model loaded on device {VISION_DEVICE}.")
        except Exception as exc:
            vision_model = None
            print(f"[Startup] Failed to load YOLO vision model: {exc}")
    print("[Startup] Initializing Qdrant vector semantic collections...")
    seed_qdrant_knowledge()
    
    # Restore the persisted telemetry snapshot into the fast Redis cache.
    cached_iot = redis_client.hgetall("telemetry")
    if not cached_iot:
        db = SessionLocal()
        try:
            snapshot = db.query(TelemetrySnapshot).order_by(
                TelemetrySnapshot.updated_at.desc()
            ).first()
            if snapshot:
                telemetry_values = {
                    "temperature": snapshot.temperature,
                    "humidity": snapshot.humidity,
                    "soil_moisture": snapshot.soil_moisture,
                    "soil_ph": snapshot.soil_ph,
                    "nitrogen": snapshot.nitrogen,
                    "phosphorus": snapshot.phosphorus,
                    "potassium": snapshot.potassium,
                    "water_level_pct": snapshot.water_level_pct
                }
                redis_client.hset("telemetry", mapping=telemetry_values)
                print("[Startup] Restored telemetry from SQL snapshot.")
            else:
                telemetry_values = {
                    "temperature": 31.5,
                    "humidity": 72.0,
                    "soil_moisture": 48.0,
                    "soil_ph": 6.7,
                    "nitrogen": 178.0,
                    "phosphorus": 41.0,
                    "potassium": 215.0,
                    "water_level_pct": 65.0
                }
                db.add(TelemetrySnapshot(**telemetry_values))
                db.commit()
                redis_client.hset("telemetry", mapping=telemetry_values)
                print("[Startup] Seeded SQL and Redis telemetry defaults.")
        finally:
            db.close()

class ChatRequest(BaseModel):
    query: str
    system_prompt: Optional[str] = None
    language: str = "en"
    need_audio: bool = False
    profile: Optional[Dict[str, Any]] = None

class TelemetryUpdate(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    soil_moisture: Optional[float] = None
    soil_ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    water_level_pct: Optional[float] = None

class LocationResolveRequest(BaseModel):
    address: str
    fallback_lat: Optional[float] = None
    fallback_lng: Optional[float] = None

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Agriva Engine", "databases": "connected"}

@app.post("/api/location/resolve")
def resolve_location(request: LocationResolveRequest):
    """Resolve a farm address using a 15-minute SQL-backed geocoding cache."""
    address = " ".join(request.address.split())
    if not address:
        raise HTTPException(status_code=422, detail="Farm address is required")

    address_key = hashlib.sha256(address.casefold().encode("utf-8")).hexdigest()
    now = datetime.datetime.utcnow()
    db = SessionLocal()
    try:
        cached = db.query(LocationCache).filter(LocationCache.address_key == address_key).first()
        if cached and (now - cached.resolved_at).total_seconds() < 900:
            return {
                "latitude": cached.latitude,
                "longitude": cached.longitude,
                "source": "database_cache",
                "cached": True
            }

        url = f"https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q={quote(address)}"
        request_obj = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Agriva/1.0 farm-location-resolver"
            }
        )
        try:
            with urlopen(request_obj, timeout=8) as response:
                results = json.loads(response.read().decode("utf-8"))
            result = results[0] if results else None
            latitude = float(result["lat"]) if result else None
            longitude = float(result["lon"]) if result else None
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            latitude = None
            longitude = None

        if latitude is not None and longitude is not None:
            if cached:
                cached.address_text = address
                cached.latitude = latitude
                cached.longitude = longitude
                cached.resolved_at = now
            else:
                db.add(LocationCache(
                    address_key=address_key,
                    address_text=address,
                    latitude=latitude,
                    longitude=longitude,
                    resolved_at=now
                ))
            db.commit()
            return {
                "latitude": latitude,
                "longitude": longitude,
                "source": "address_geocode",
                "cached": False
            }

        if request.fallback_lat is not None and request.fallback_lng is not None:
            return {
                "latitude": request.fallback_lat,
                "longitude": request.fallback_lng,
                "source": "saved_coordinates",
                "cached": False
            }
        raise HTTPException(status_code=502, detail="Could not resolve farm address")
    finally:
        db.close()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY", "")
)

VISION_LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "pa": "Punjabi",
    "mr": "Marathi",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "gu": "Gujarati",
    "bn": "Bengali",
    "ml": "Malayalam",
    "or": "Odia",
}

def get_vision_advice(labels: list[str], language: str) -> tuple[dict[str, dict[str, str]], Optional[str]]:
    """Generate cautious, crop-specific severity and treatment guidance for detections."""
    language_name = VISION_LANGUAGE_NAMES.get(language, "English")
    prompt = f"""
You are Agriva, an agricultural plant-health advisor.
The computer vision model detected these labels in a crop image:
{json.dumps(labels, ensure_ascii=False)}

For every label, return practical guidance in {language_name}. A label may be a
crop or plant class rather than a confirmed disease. Do not invent a disease:
when uncertain, use a conservative severity and say that field confirmation is
needed. Recommend only applicable actions, prioritizing sanitation, monitoring,
watering, isolation, or consultation. Mention a pesticide or fungicide only if
it is appropriate, and include the active ingredient or product type plus a
reminder to follow the local label and agricultural officer guidance.

Return ONLY valid JSON in this shape:
{{
  "label": {{
    "severity": "Low|Moderate|High|Critical|Uncertain",
    "treatment": "short actionable treatment in the requested language"
  }}
}}
"""
    try:
        completion = client.chat.completions.create(
            model="google/gemma-4-31b-it",
            messages=[
                {"role": "system", "content": "Return valid JSON only. Never use markdown fences."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            top_p=0.8,
            max_tokens=700,
            stream=False,
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Vision advice model returned an empty response.")
        advice = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
        if not isinstance(advice, dict):
            raise ValueError("Vision advice model returned an invalid JSON object.")
        return {
            label: {
                "severity": str(value.get("severity", "Uncertain")),
                "treatment": str(value.get("treatment", "Confirm the issue with a local agricultural expert.")),
            }
            for label, value in advice.items()
            if isinstance(value, dict)
        }, None
    except Exception as exc:
        return {}, str(exc)

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi (Devanagari)",
    "pa": "Punjabi (Gurmukhi)",
    "mr": "Marathi (Devanagari)",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "gu": "Gujarati",
    "bn": "Bengali",
    "ml": "Malayalam",
    "or": "Odia",
}

@app.post("/api/chatbot")
def chatbot_endpoint(request: ChatRequest):
    language_name = LANGUAGE_NAMES.get(request.language, "English")
    default_system_prompt = f"""
You are Agriva, an AI assistant specialized ONLY in agriculture.
The user's selected language is {language_name} (code: {request.language}).
Write the entire answer in that language. This includes the summary, headings,
category labels, table headings, bullet labels, and closing text. Do not switch
to English in the middle of the answer. Keep unavoidable crop names, product
names, and standard abbreviations only when they are proper names or have no
clear translation.

Your domain includes:
- Crop diseases
- Plant health
- Fertilizers
- Irrigation
- Weather for farming
- Soil analysis
- Livestock
- Government agricultural schemes
- Mandi prices
- Precision agriculture

If a user asks anything outside agriculture, farming, crops, livestock,
horticulture, or rural farming practices, do not answer the question.

Instead reply politely:

"I'm Agriva, an agriculture assistant. I can only help with farming-related
questions such as crop diseases, fertilizers, irrigation, weather, soil health,
and government schemes."

Never provide programming code, mathematics, general knowledge, essays,
jokes, recipes, or other unrelated content.
"""

    system_prompt = request.system_prompt if request.system_prompt else default_system_prompt
    completion = client.chat.completions.create(
        model="google/gemma-4-31b-it",
        messages=[
            {
            "role": "system",
            "content": f"{request.system_prompt}\n\n{default_system_prompt}" if request.system_prompt else default_system_prompt
        },
            {
                "role": "user",
                "content": request.query
            }
        ],
        temperature=0.2,
        top_p=0.8,
        max_tokens=1000,
        stream=False
    )

    answer = completion.choices[0].message.content
    print(f"[Chatbot] User Query: {request.query}\n[Chatbot] Response: {answer}")

    return {
        "answer": answer
    }

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    """Executes the LangGraph Multi-Agent network."""
    profile = request.profile or {}
    allowed_profile_fields = {
        "farmer_name",
        "contact_number",
        "location",
        "address",
        "current_crop",
        "land_size_hectares",
        "soil_type",
        "ph",
        "irrigation_type",
        "budget",
        "lat",
        "lng",
        "temperature",
        "humidity",
        "soil_moisture",
        "nitrogen",
        "phosphorus",
        "potassium",
        "water_level_pct"
    }

    # Load latest telemetry from Redis cache
    cached = redis_client.hgetall("telemetry")
    if cached:
        profile.update({
            "ph": float(cached.get("soil_ph", 6.7)),
            "soil_moisture": float(cached.get("soil_moisture", 48.0)),
            "temperature": float(cached.get("temperature", 31.5)),
            "humidity": float(cached.get("humidity", 72.0)),
            "nitrogen": float(cached.get("nitrogen", 178)),
            "phosphorus": float(cached.get("phosphorus", 41)),
            "potassium": float(cached.get("potassium", 215)),
            "water_level_pct": float(cached.get("water_level_pct", 65))
        })

    safe_profile = {key: value for key, value in profile.items() if key in allowed_profile_fields}

    is_telemetry_query = "telemetry status" in request.query.lower()
    cache_key = hashlib.sha256(json.dumps({
        "query": request.query.strip().casefold(),
        "language": request.language,
        "profile": safe_profile
    }, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    cache_db = SessionLocal()
    if is_telemetry_query and not request.need_audio:
        try:
            cached_output = cache_db.query(AgentOutputCache).filter(
                AgentOutputCache.cache_key == cache_key
            ).first()
            if cached_output and (
                datetime.datetime.utcnow() - cached_output.created_at
            ).total_seconds() < 900:
                print(f"[Agent Cache] HIT telemetry output for {request.query}")
                return json.loads(cached_output.payload)
            print(f"[Agent Cache] MISS telemetry output for {request.query}")
        finally:
            cache_db.close()
    else:
        cache_db.close()

    initial_state = AgentState(
        user_query=request.query,
        language=request.language,
        farmer_profile=safe_profile
    )
    
    try:
        final_state = compiled_graph.invoke(initial_state)
        if isinstance(final_state, dict):
            plan = final_state.get("execution_plan", [])
            vision = final_state.get("vision_results")
            weather = final_state.get("weather_info")
            soil = final_state.get("soil_data")
            market = final_state.get("market_rates")
            schemes = final_state.get("schemes", [])
            medical = final_state.get("medical_advice")
            disaster = final_state.get("disaster_alerts")
            tutorials = final_state.get("tutorials", [])
            explanation = final_state.get("explanation", "")
            profile = final_state.get("farmer_profile", {})
        else:
            plan = final_state.execution_plan
            vision = final_state.vision_results
            weather = final_state.weather_info
            soil = final_state.soil_data
            market = final_state.market_rates
            schemes = final_state.schemes
            medical = final_state.medical_advice
            disaster = final_state.disaster_alerts
            tutorials = final_state.tutorials
            explanation = final_state.explanation
            profile = final_state.farmer_profile

        if request.need_audio:
            speech_filename = f"response_{request.language}.mp3"
            speech_output_path = os.path.join(VOICE_DIR, speech_filename)
            try:
                voice_content = clean_text_for_tts(explanation)
                tts = gTTS(text=voice_content, lang=request.language if request.language in ["en", "hi", "ta", "te", "bn", "gu", "kn", "ml", "mr", "pa"] else "en")
                tts.save(speech_output_path)
                speech_url = f"/static/voice/{speech_filename}"
            except Exception:
                speech_url = None

        response_payload = {
            "execution_plan": plan,
            "vision_results": vision,
            "weather_info": weather,
            "soil_data": soil,
            "market_rates": market,
            "schemes": schemes,
            "medical_advice": medical,
            "disaster_alerts": disaster,
            "tutorials": tutorials,
            "explanation": explanation,
            "profile": profile,
            "speech_url": speech_url if request.need_audio else None
        }

        if is_telemetry_query and not request.need_audio:
            cache_db = SessionLocal()
            try:
                cached_output = cache_db.query(AgentOutputCache).filter(
                    AgentOutputCache.cache_key == cache_key
                ).first()
                serialized_payload = json.dumps(response_payload, default=str)
                if cached_output:
                    cached_output.payload = serialized_payload
                    cached_output.created_at = datetime.datetime.utcnow()
                else:
                    cache_db.add(AgentOutputCache(
                        cache_key=cache_key,
                        payload=serialized_payload,
                        created_at=datetime.datetime.utcnow()
                    ))
                cache_db.commit()
                print(f"[Agent Cache] STORED telemetry output for {request.query}")
            finally:
                cache_db.close()

        return response_payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vision/analyze")
async def analyze_crop_image(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    """Run the startup-loaded YOLO leaf detector and return an annotated image."""
    if vision_model is None:
        raise HTTPException(status_code=503, detail="Vision model is unavailable.")

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG, or WEBP image.")

    image_bytes = await file.read()
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.")

    try:
        height, width = image.shape[:2]
        results = vision_model.predict(source=image, device=VISION_DEVICE, verbose=False)
        result = results[0]
        detections = []
        raw_detections = []
        if result.boxes is not None:
            names = result.names
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().tolist()
                confidence = float(box.conf[0].cpu().item())
                class_id = int(box.cls[0].cpu().item())
                label = names.get(class_id, str(class_id)) if isinstance(names, dict) else str(class_id)
                raw_detections.append({
                    "label": label,
                    "confidence": confidence,
                    "bbox": [
                        (y1 / height) * 100,
                        (x1 / width) * 100,
                        ((x2 - x1) / width) * 100,
                        ((y2 - y1) / height) * 100,
                    ],
                    "bbox_pixels": [x1, y1, x2, y2],
                })

        detected_labels = sorted({detection["label"] for detection in raw_detections})
        advice_by_label, advice_error = (
            get_vision_advice(detected_labels, language)
            if detected_labels
            else ({}, None)
        )
        for detection in raw_detections:
            advice = advice_by_label.get(detection["label"], {})
            detection["severity"] = advice.get("severity", "Uncertain")
            detection["remedy"] = advice.get(
                "treatment",
                "No AI treatment guidance was available; confirm the diagnosis with a local agricultural expert.",
            )
            detections.append(detection)

        annotated_image = result.plot()
        output_name = f"vision_{uuid.uuid4().hex}.jpg"
        output_path = os.path.join(UPLOAD_DIR, output_name)
        if not cv2.imwrite(output_path, annotated_image):
            raise RuntimeError("Could not write the annotated image.")

        return {
            "image_url": f"/static/uploads/{output_name}",
            "detections": detections,
            "device": str(VISION_DEVICE),
            "model": os.path.basename(MODEL_PATH),
            "advice_language": language,
            "advice_source": "llm" if not advice_error else "fallback",
            "advice_error": advice_error,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Vision inference failed: {exc}") from exc


recognizer = sr.Recognizer()

# Map short language codes to Google Speech Recognition locales
LOCALE_MAP = {
    "en": "en-IN",
    "hi": "hi-IN",
    "pa": "pa-IN",
    "mr": "mr-IN",
    "te": "te-IN",
    "ta": "ta-IN",
    "kn": "kn-IN",
    "gu": "gu-IN",
    "bn": "bn-IN",
    "ml": "ml-IN",
    "or": "or-IN"
}

@app.post("/api/voice/process")
async def process_voice(
    file: UploadFile = File(...),
    language: str = Form("en"),
    farmer_profile: str = Form(None)
):
    """Processes regional language audio recordings with format conversion."""
    
    raw_audio_path = os.path.join(VOICE_DIR, f"raw_{file.filename}")
    converted_wav_path = os.path.join(VOICE_DIR, f"converted_{file.filename}.wav")
    
    # 1. Save incoming raw browser audio file
    with open(raw_audio_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Convert incoming audio (WebM/OGG/etc.) to proper PCM WAV using pydub
    try:
        sound = AudioSegment.from_file(raw_audio_path)
        sound.export(converted_wav_path, format="wav")
    except Exception as e:
        print(f"Audio conversion failed: {e}")
        converted_wav_path = raw_audio_path  # Fallback
        
    # 3. Transcribe the converted PCM WAV file
    target_locale = LOCALE_MAP.get(language, "en-IN")
    try:
        with sr.AudioFile(converted_wav_path) as source:
            audio_data = recognizer.record(source)
            transcribed_text = recognizer.recognize_google(audio_data, language=target_locale)
    except sr.UnknownValueError:
        transcribed_text = "Audio unclear. Please try speaking again."
    except Exception as e:
        print(f"Speech recognition error: {e}")
        transcribed_text = "Could not process audio transcription."
    finally:
        # Cleanup temporary files
        for p in [raw_audio_path, converted_wav_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
    
    # 4. Agent Workflow
    initial_state = AgentState(
        user_query=transcribed_text,
        language=language,
        farmer_profile=json.loads(farmer_profile) or {}
    )
    final_state = compiled_graph.invoke(initial_state)
    
    if isinstance(final_state, dict):
        explanation = final_state.get("explanation", "")
        plan = final_state.get("execution_plan", [])
    else:
        explanation = final_state.explanation
        plan = final_state.execution_plan
    
    # 5. Generate TTS response
    speech_filename = f"response_{language}.mp3"
    speech_output_path = os.path.join(VOICE_DIR, speech_filename)
    voice_content = explanation if explanation else "Advice processing completed."

    try:
        voice_content = clean_text_for_tts(voice_content)
        tts = gTTS(text=voice_content, lang=language if language in ["en", "hi", "ta", "te", "bn", "gu", "kn", "ml", "mr", "pa"] else "en")
        tts.save(speech_output_path)
        speech_url = f"/static/voice/{speech_filename}"
    except Exception:
        speech_url = None
        
    return {
        "transcription": transcribed_text,
        "explanation": explanation,
        "speech_url": speech_url,
        "agents_routed": plan
    }

@app.get("/api/iot/telemetry")
def get_telemetry():
    """Retrieve telemetry values directly from Redis cache."""
    cached = redis_client.hgetall("telemetry")
    if not cached:
        raise HTTPException(status_code=404, detail="No telemetry cached.")
        
    return {
        "temperature": float(cached.get("temperature", 30)),
        "humidity": float(cached.get("humidity", 70)),
        "soil_moisture": float(cached.get("soil_moisture", 45)),
        "soil_ph": float(cached.get("soil_ph", 6.5)),
        "nitrogen": float(cached.get("nitrogen", 150)),
        "phosphorus": float(cached.get("phosphorus", 40)),
        "potassium": float(cached.get("potassium", 200)),
        "water_level_pct": float(cached.get("water_level_pct", 50))
    }

@app.post("/api/iot/telemetry")
def update_telemetry(data: TelemetryUpdate):
    """Saves incoming IoT sensor updates in the Redis cache."""
    # Convert numeric values to strings for Redis hash storage compatibility
    values = data.model_dump(exclude_none=True)
    limits = {
        "temperature": (-40, 70),
        "humidity": (0, 100),
        "soil_moisture": (0, 100),
        "soil_ph": (0, 14),
        "nitrogen": (0, 10000),
        "phosphorus": (0, 10000),
        "potassium": (0, 10000),
        "water_level_pct": (0, 100)
    }
    for key, value in values.items():
        minimum, maximum = limits[key]
        if value < minimum or value > maximum:
            raise HTTPException(
                status_code=422,
                detail=f"{key} must be between {minimum} and {maximum}"
            )

    stringified_map = {str(k): str(v) for k, v in values.items()}
    redis_client.hset("telemetry", mapping=stringified_map)

    db = SessionLocal()
    try:
        snapshot = db.query(TelemetrySnapshot).order_by(
            TelemetrySnapshot.updated_at.desc()
        ).first()
        if not snapshot:
            snapshot = TelemetrySnapshot(
                temperature=31.5,
                humidity=72.0,
                soil_moisture=48.0,
                soil_ph=6.7,
                nitrogen=178.0,
                phosphorus=41.0,
                potassium=215.0,
                water_level_pct=65.0
            )
            db.add(snapshot)
        for key, value in values.items():
            setattr(snapshot, key, value)
        snapshot.updated_at = datetime.datetime.utcnow()
        db.commit()
    finally:
        db.close()

    return {"status": "success", "cached_telemetry": redis_client.hgetall("telemetry")}

@app.get("/api/marketplace/prices")
def get_mandi_prices():
    return MANDI_PRICES

@app.get("/api/mandi/records")
def get_mandi_records():
    """Proxy current Agmarknet records without exposing the government API key."""
    api_key = (os.getenv("GOV_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="GOV_API_KEY is not configured")

    query = urlencode({
        "api-key": api_key,
        "format": "json",
        "limit": "10",
        "sort[arrival_date]": "desc",
    })
    request = Request(
        f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?{query}",
        headers={"User-Agent": "Agriva/1.0"},
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 403:
            print("[Mandi] Agmarknet rejected GOV_API_KEY; frontend will use its explicit fallback path.")
            return {
                "records": [],
                "source": "upstream_unavailable",
                "error": "Agmarknet rejected GOV_API_KEY"
            }
        raise HTTPException(status_code=502, detail=f"Agmarknet returned HTTP {error.code}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail="Unable to fetch Agmarknet records") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise HTTPException(status_code=502, detail="Agmarknet returned an invalid records payload")

    return payload


def clean_text_for_tts(text: str) -> str:
    # Remove Markdown bold and italic markers
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)

    # Remove bullet markers at the start of lines
    text = re.sub(r"(?m)^\s*[-*•▪]\s+", "", text)

    # Remove Markdown heading markers
    text = re.sub(r"(?m)^\s*#{1,6}\s+", "", text)

    # Replace table separators and pipes
    text = text.replace("|", " ")
    text = re.sub(r"(?m)^\s*[-:]{3,}\s*$", "", text)

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()