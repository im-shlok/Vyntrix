import os
import shutil
import json
import hashlib
import datetime
import time
import threading
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request as URLRequest, urlopen
from gtts import gTTS
from dotenv import load_dotenv
import speech_recognition as sr
from pydub import AudioSegment
from fastapi import Depends, FastAPI, Request, Response, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
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
    User,
    UserSession,
    LocationCache,
    AgentOutputCache,
    CommunityPost,
    FarmerProfile,
    TelemetrySnapshot,
    create_session,
    hash_password,
    hash_session_token,
    get_db,
    user_for_session,
    verify_password,
)
from app.core.redis_client import redis_client
from app.core.chatbot import LANGUAGE_NAMES, ask_agriva
from app.core.llm_client import chat_completion
from app.rag import get_status as rag_status
from app.rag import CATEGORY_AGRONOMY, index_corpus, intent_scores, retrieve, warm_up_intents
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

# Uploaded/annotated vision images are transient: they are served once to the
# client that just analyzed them, then removed. A new upload clears the previous
# image immediately, and this TTL sweeps anything left behind (e.g. if the user
# never uploads again). Override with VISION_UPLOAD_TTL_SECONDS in .env.
VISION_UPLOAD_TTL_SECONDS = int(os.getenv("VISION_UPLOAD_TTL_SECONDS", "900"))  # 15 minutes
VISION_SWEEP_INTERVAL_SECONDS = 60


def delete_vision_uploads() -> int:
    """Delete every annotated vision image in the uploads dir. Returns count."""
    removed = 0
    for name in os.listdir(UPLOAD_DIR):
        if not name.startswith("vision_"):
            continue
        try:
            os.remove(os.path.join(UPLOAD_DIR, name))
            removed += 1
        except OSError:
            pass  # already gone or held open; skip it
    return removed


def sweep_expired_vision_uploads() -> int:
    """Delete vision images older than the TTL. Returns count removed."""
    cutoff = time.time() - VISION_UPLOAD_TTL_SECONDS
    removed = 0
    for name in os.listdir(UPLOAD_DIR):
        if not name.startswith("vision_"):
            continue
        path = os.path.join(UPLOAD_DIR, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                removed += 1
        except OSError:
            pass
    return removed


def _vision_cleanup_loop():
    while True:
        time.sleep(VISION_SWEEP_INTERVAL_SECONDS)
        try:
            sweep_expired_vision_uploads()
        except Exception as exc:
            print(f"[VisionCleanup] Sweep failed: {exc}")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount MCP Router
app.include_router(mcp_router)

# Server startup seeding pipeline
@app.on_event("startup")
def on_startup():
    print("[Startup] Initializing persistent SQLAlchemy tables...")
    init_db()
    # Vision uploads are transient; drop anything left from a previous run and
    # keep a background sweeper removing expired images while the server is up.
    stale = delete_vision_uploads()
    if stale:
        print(f"[Startup] Cleared {stale} stale vision upload(s).")
    threading.Thread(target=_vision_cleanup_loop, daemon=True).start()
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
    print("[Startup] Building RAG corpus and vector index...")
    try:
        status = index_corpus()
        warm_up_intents()
        print(
            f"[Startup] RAG ready: {status['documents_indexed']} documents, "
            f"mode={status['retrieval_mode']}, store={status['vector_store']}."
        )
    except Exception as exc:
        # Retrieval degrades to lexical on its own; never block startup for it.
        print(f"[Startup] RAG indexing failed: {exc}")
    
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


SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "agriva_session")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 24 * 30)))
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"


class AuthRegisterRequest(BaseModel):
    # ``email`` is accepted as an alias for clients that call their account ID
    # an email; the server keeps one normalized username identity.
    username: Optional[str] = None
    email: Optional[str] = None
    password: str = Field(min_length=8, max_length=256)
    farmer_name: Optional[str] = None
    contact_number: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    current_crop: Optional[str] = None
    land_size_hectares: Optional[float] = Field(default=None, ge=0)
    soil_type: Optional[str] = None
    ph: Optional[float] = Field(default=None, ge=0, le=14)
    irrigation_type: Optional[str] = None
    budget: Optional[str] = None
    language: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class AuthLoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str = Field(min_length=1, max_length=256)


class ProfilePatchRequest(BaseModel):
    farmer_name: Optional[str] = None
    contact_number: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    current_crop: Optional[str] = None
    land_size_hectares: Optional[float] = Field(default=None, ge=0)
    soil_type: Optional[str] = None
    ph: Optional[float] = Field(default=None, ge=0, le=14)
    irrigation_type: Optional[str] = None
    budget: Optional[str] = None
    language: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class CommunityPostRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    tag: str = Field(default="#General", max_length=50)


def _serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _serialize_profile(profile: FarmerProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "farmer_name": profile.farmer_name,
        "contact_number": profile.contact_number or "",
        "location": profile.location,
        "address": profile.address or "",
        "current_crop": profile.current_crop,
        "land_size_hectares": profile.land_size_hectares,
        "soil_type": profile.soil_type,
        "ph": profile.ph,
        "irrigation_type": profile.irrigation_type,
        "budget": profile.budget,
        "language": profile.language,
        "lat": profile.latitude,
        "lng": profile.longitude,
    }


def _default_profile_values() -> dict[str, Any]:
    return {
        "farmer_name": "Ramesh Kumar",
        "contact_number": "",
        "location": "Bhatinda, Punjab",
        "address": "",
        "current_crop": "Tomato",
        "land_size_hectares": 1.5,
        "soil_type": "Loam",
        "ph": 6.7,
        "irrigation_type": "Drip",
        "budget": "Medium",
        "language": "en",
    }


def _get_or_create_profile(db, user: User) -> FarmerProfile:
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == user.id).first()
    if profile:
        return profile
    profile = FarmerProfile(user_id=user.id, **_default_profile_values())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _account_identifier(username: Optional[str], email: Optional[str]) -> str:
    for candidate in (username, email):
        normalized = (candidate or "").strip().casefold()
        if normalized:
            return normalized
    return ""


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def get_current_user(request: Request, db=Depends(get_db)) -> User:
    user = user_for_session(db, request.cookies.get(SESSION_COOKIE_NAME))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def get_optional_user(request: Request, db=Depends(get_db)) -> Optional[User]:
    return user_for_session(db, request.cookies.get(SESSION_COOKIE_NAME))


def _serialize_post(db, post: CommunityPost) -> dict[str, Any]:
    user = db.query(User).filter(User.id == post.user_id).first()
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == post.user_id).first()
    display_name = (profile.farmer_name if profile and profile.farmer_name else None) or (
        user.username if user else "Farmer Node"
    )
    location = (profile.location if profile and profile.location else None) or "Self Farm Node"
    created_at = post.created_at.isoformat() if post.created_at else None
    return {
        "id": post.id,
        "user_id": post.user_id,
        "username": user.username if user else None,
        "author": display_name,
        "location": location,
        "tag": post.tag,
        "content": post.content,
        "timestamp": created_at,
        "created_at": created_at,
    }


def _auth_payload(user: User, profile: FarmerProfile) -> dict[str, Any]:
    return {"user": _serialize_user(user), "profile": _serialize_profile(profile)}


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(request: AuthRegisterRequest, response: Response, db=Depends(get_db)):
    username = _account_identifier(request.username, request.email)
    if not username:
        raise HTTPException(status_code=422, detail="Username or email is required")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Username already registered")

    user = User(username=username, password_hash=hash_password(request.password))
    db.add(user)
    try:
        db.flush()
        profile_values = _default_profile_values()
        supplied = request.model_dump(exclude_unset=True)
        field_map = {"lat": "latitude", "lng": "longitude"}
        profile_fields = {
            "farmer_name", "contact_number", "location", "address", "current_crop",
            "land_size_hectares", "soil_type", "ph", "irrigation_type", "budget",
            "language", "lat", "lng",
        }
        for key in profile_fields:
            if key in supplied and supplied[key] is not None:
                profile_values[field_map.get(key, key)] = supplied[key]
        profile = FarmerProfile(user_id=user.id, **profile_values)
        db.add(profile)
        db.commit()
        db.refresh(user)
        token = create_session(db, user, SESSION_TTL_SECONDS)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already registered")

    _set_session_cookie(response, token)
    return _auth_payload(user, profile)


@app.post("/api/auth/login")
def login(request: AuthLoginRequest, response: Response, db=Depends(get_db)):
    username = _account_identifier(request.username, request.email)
    user = db.query(User).filter(User.username == username).first() if username else None
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    profile = _get_or_create_profile(db, user)
    token = create_session(db, user, SESSION_TTL_SECONDS)
    _set_session_cookie(response, token)
    return _auth_payload(user, profile)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        session = db.query(UserSession).filter(UserSession.token_hash == hash_session_token(token)).first()
        if session:
            session.revoked = True
            db.commit()
    _clear_session_cookie(response)
    return {"status": "logged_out"}


@app.get("/api/auth/me")
def me(user: User = Depends(get_current_user), db=Depends(get_db)):
    return _auth_payload(user, _get_or_create_profile(db, user))


@app.get("/api/profile")
@app.get("/api/profile/me")
def get_profile(user: User = Depends(get_current_user), db=Depends(get_db)):
    return _serialize_profile(_get_or_create_profile(db, user))


@app.patch("/api/profile")
@app.patch("/api/profile/me")
def update_profile(
    request: ProfilePatchRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    profile = _get_or_create_profile(db, user)
    values = request.model_dump(exclude_unset=True)
    field_map = {"lat": "latitude", "lng": "longitude"}
    for key, value in values.items():
        setattr(profile, field_map.get(key, key), value)
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


@app.get("/api/community/posts")
@app.get("/api/community")
def get_community_posts(
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    posts = (
        db.query(CommunityPost)
        .order_by(CommunityPost.created_at.desc(), CommunityPost.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_serialize_post(db, post) for post in posts]


@app.post("/api/community/posts", status_code=status.HTTP_201_CREATED)
@app.post("/api/community", status_code=status.HTTP_201_CREATED)
def create_community_post(
    request: CommunityPostRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    tag = request.tag.strip() or "#General"
    if not tag.startswith("#"):
        tag = f"#{tag}"
    post = CommunityPost(user_id=user.id, tag=tag[:50], content=request.content.strip())
    if not post.content:
        raise HTTPException(status_code=422, detail="Post content is required")
    db.add(post)
    db.commit()
    db.refresh(post)
    return _serialize_post(db, post)

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
        request_obj = URLRequest(
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

def normalize_vision_label(label: str) -> str:
    """Turn a YOLO class name into natural language for retrieval.

    Dataset labels arrive as "Tomato___Early_blight" or "tomato_late_blight",
    which match nothing in a prose corpus until the separators are stripped.
    """
    cleaned = re.sub(r"_{2,}", " ", label)
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def get_vision_advice(labels: list[str], language: str) -> tuple[dict[str, dict[str, str]], Optional[str]]:
    """Generate cautious, crop-specific treatment guidance for detections."""
    language_name = LANGUAGE_NAMES.get(language, "English")

    # Ground the advice in retrieved agronomy documents. Without this the model
    # is told "do not invent a disease" while being given nothing to work from.
    reference_block = ""
    try:
        references = []
        seen_ids = set()
        for label in labels:
            for document in retrieve(normalize_vision_label(label), limit=2,
                                     category=CATEGORY_AGRONOMY):
                if document.id in seen_ids:
                    continue
                seen_ids.add(document.id)
                references.append(f"({document.source}) {document.text}")
        if references:
            reference_block = (
                "\nUse the following retrieved reference material as the "
                "authoritative basis for your guidance. Prefer it over your "
                "own prior knowledge, and do not contradict it:\n"
                + "\n".join(f"- {reference}" for reference in references)
                + "\n"
            )
    except Exception as exc:
        print(f"[Vision] Retrieval unavailable, advising without grounding: {exc}")

    prompt = f"""
You are Agriva, an agricultural plant-health advisor.
The computer vision model detected these labels in a crop image:
{json.dumps(labels, ensure_ascii=False)}
{reference_block}
For every label, return practical guidance in {language_name}. A label may be a
crop or plant class rather than a confirmed disease. Do not invent a disease:
when uncertain, say that field confirmation is needed. Recommend only applicable
actions, prioritizing sanitation, monitoring,
watering, isolation, or consultation. Mention a pesticide or fungicide only if
it is appropriate, and include the active ingredient or product type plus a
reminder to follow the local label and agricultural officer guidance.

Return ONLY valid JSON in this shape:
{{
  "label": {{
    "treatment": "short actionable treatment in the requested language"
  }}
}}
"""
    try:
        # Reasoning tokens count against max_tokens on the Groq models, and
        # non-English JSON is token-heavy, so 700 could truncate the JSON.
        content, _ = chat_completion(
            [
                {"role": "system", "content": "Return valid JSON only. Never use markdown fences."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            top_p=0.8,
            max_tokens=1500,
        )
        if not content:
            raise ValueError("Every vision advice model failed or returned an empty response.")
        advice = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
        if not isinstance(advice, dict):
            raise ValueError("Vision advice model returned an invalid JSON object.")
        return {
            label: {
                "treatment": str(value.get("treatment", "Confirm the issue with a local agricultural expert.")),
            }
            for label, value in advice.items()
            if isinstance(value, dict)
        }, None
    except Exception as exc:
        return {}, str(exc)

VISION_SEVERITY_TRANSLATIONS = {
    "en": {"Low": "Low", "Moderate": "Moderate", "High": "High", "Critical": "Critical"},
    "hi": {"Low": "कम", "Moderate": "मध्यम", "High": "उच्च", "Critical": "गंभीर"},
    "pa": {"Low": "ਘੱਟ", "Moderate": "ਦਰਮਿਆਨਾ", "High": "ਉੱਚ", "Critical": "ਗੰਭੀਰ"},
    "mr": {"Low": "कमी", "Moderate": "मध्यम", "High": "उच्च", "Critical": "गंभीर"},
    "te": {"Low": "తక్కువ", "Moderate": "మధ్యస్థ", "High": "అధిక", "Critical": "తీవ్రమైన"},
    "ta": {"Low": "குறைவு", "Moderate": "மிதமான", "High": "அதிகம்", "Critical": "மிகவும் தீவிரம்"},
    "kn": {"Low": "ಕಡಿಮೆ", "Moderate": "ಮಧ್ಯಮ", "High": "ಹೆಚ್ಚು", "Critical": "ಗಂಭೀರ"},
    "gu": {"Low": "ઓછું", "Moderate": "મધ્યમ", "High": "વધુ", "Critical": "ગંભીર"},
    "bn": {"Low": "কম", "Moderate": "মাঝারি", "High": "উচ্চ", "Critical": "গুরুতর"},
    "ml": {"Low": "കുറവ്", "Moderate": "മിതമായ", "High": "ഉയർന്ന", "Critical": "ഗുരുതരം"},
    "or": {"Low": "କମ୍", "Moderate": "ମଧ୍ୟମ", "High": "ଉଚ୍ଚ", "Critical": "ଗୁରୁତର"},
}

def calculate_vision_severity(confidence: float, language: str) -> tuple[str, str]:
    """Map confidence to a stable severity key and localized display value."""
    if confidence >= 0.80:
        severity_key = "Critical"
    elif confidence >= 0.60:
        severity_key = "High"
    elif confidence >= 0.40:
        severity_key = "Moderate"
    else:
        severity_key = "Low"
    translated = VISION_SEVERITY_TRANSLATIONS.get(language, VISION_SEVERITY_TRANSLATIONS["en"])
    return severity_key, translated[severity_key]

@app.post("/api/chatbot")
def chatbot_endpoint(request: ChatRequest):
    answer, _ = ask_agriva(request.query, system_prompt=request.system_prompt, language=request.language)
    if not answer:
        # An error status, not an empty answer, so VoiceAssistant falls back
        # to its offline pipeline.
        raise HTTPException(status_code=503, detail="All chat models are unavailable.")
    return {
        "answer": answer
    }

@app.post("/api/chat")
def chat_endpoint(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_user),
):
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
    if current_user:
        # This context marker is added only from the HttpOnly session. It is
        # consumed by memory_agent and never exposed in the response profile.
        safe_profile["_user_id"] = current_user.id

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
                cached_payload = json.loads(cached_output.payload)
                # Entries written when the LLM failed, or before
                # explanation_source existed, hold the non-LLM fallback text.
                # Serving one would repeat it for the rest of the 15 minutes.
                source = cached_payload.get("explanation_source")
                if source and source != "fallback":
                    print(f"[Agent Cache] HIT telemetry output for {request.query}")
                    return cached_payload
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
            retrieved_docs = final_state.get("retrieved_docs", [])
            routing_mode = final_state.get("routing_mode", "keyword")
            explanation_source = final_state.get("explanation_source", "")
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
            retrieved_docs = final_state.retrieved_docs
            routing_mode = final_state.routing_mode
            explanation_source = final_state.explanation_source

        explanation = re.sub(r"\[\d+\]", "", explanation)
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
            "retrieved_docs": retrieved_docs,
            "routing_mode": routing_mode,
            # "provider:model" that wrote the explanation, or "fallback".
            "explanation_source": explanation_source,
            "speech_url": speech_url if request.need_audio else None
        }

        if is_telemetry_query and not request.need_audio and explanation_source != "fallback":
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

    # Only the most recent analysis is ever shown, so drop previous uploads now
    # rather than letting them pile up until the TTL sweep catches them.
    delete_vision_uploads()

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
            severity_key, localized_severity = calculate_vision_severity(
                detection["confidence"],
                language,
            )
            detection["severity"] = localized_severity
            detection["severity_key"] = severity_key
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

@app.get("/api/rag/status")
def rag_status_endpoint():
    """Report what the retriever actually indexed and which mode it is in.

    `retrieval_mode` is the field to watch: "lexical" means dense retrieval is
    unavailable and results are BM25-only, which otherwise looks like a quality
    regression rather than a degraded backend.
    """
    return rag_status()


@app.get("/api/rag/search")
def rag_search_endpoint(
    q: str,
    category: Optional[str] = None,
    limit: int = 4,
    explain_routing: bool = False,
):
    """Inspect retrieval directly, without going through the agent graph."""
    if not q.strip():
        raise HTTPException(status_code=422, detail="Query 'q' is required")
    limit = max(1, min(limit, 20))

    documents = retrieve(q, limit=limit, category=category)
    payload = {
        "query": q,
        "category": category,
        "count": len(documents),
        "results": [document.to_dict() for document in documents],
    }
    if explain_routing:
        # Per-intent cosine scores behind the planner's routing decision.
        from app.rag import embed_query as _embed_query
        payload["intent_scores"] = intent_scores(_embed_query(q))
    return payload


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
    request = URLRequest(
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
    # Strip citation markers so gTTS does not read "[1]" aloud as "one"
    text = re.sub(r"\[\d+\]", "", text)

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
