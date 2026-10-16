import os
import datetime
import hashlib
import hmac
import secrets
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL with fallback to local SQLite database file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kisaan.db")

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception:
    # Safe secondary fallback in case of driver configuration anomalies
    engine = create_engine("sqlite:///./kisaan.db", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Farmer profile model
class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    # Nullable for backwards compatibility with the original seeded profile.
    # New profiles are always associated with a server-owned User.
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=True)
    farmer_name = Column(String(100), default="Ramesh Kumar")
    contact_number = Column(String(30), default="")
    location = Column(String(100), default="Bhatinda, Punjab")
    address = Column(String(500), default="")
    current_crop = Column(String(50), default="Tomato")
    land_size_hectares = Column(Float, default=1.5)
    soil_type = Column(String(50), default="Loam")
    ph = Column(Float, default=6.7)
    irrigation_type = Column(String(50), default="Drip")
    budget = Column(String(50), default="Medium")
    language = Column(String(10), default="en")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)


class User(Base):
    """Application account; password_hash never contains a plaintext password."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class UserSession(Base):
    """Opaque, revocable server-side sessions keyed by a hash of the cookie token."""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tag = Column(String(50), default="#General", nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

class LocationCache(Base):
    __tablename__ = "location_cache"

    id = Column(Integer, primary_key=True, index=True)
    address_key = Column(String(64), unique=True, index=True, nullable=False)
    address_text = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    resolved_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class AgentOutputCache(Base):
    __tablename__ = "agent_output_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(64), unique=True, index=True, nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class TelemetrySnapshot(Base):
    __tablename__ = "telemetry_snapshot"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False, default=31.5)
    humidity = Column(Float, nullable=False, default=72.0)
    soil_moisture = Column(Float, nullable=False, default=48.0)
    soil_ph = Column(Float, nullable=False, default=6.7)
    nitrogen = Column(Float, nullable=False, default=178.0)
    phosphorus = Column(Float, nullable=False, default=41.0)
    potassium = Column(Float, nullable=False, default=215.0)
    water_level_pct = Column(Float, nullable=False, default=65.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

# Conversation chat log model
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    role = Column(String(20)) # user, assistant, system
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Database session dependency injector
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize tables, upgrading the original SQLite profile table in place."""
    Base.metadata.create_all(bind=engine)

    # ``create_all`` intentionally does not alter existing tables. The shipped
    # database predates authenticated profiles, so add only the new nullable
    # columns needed by that table. This keeps existing local installs usable
    # without requiring Alembic for this small application.
    if "sqlite" in DATABASE_URL:
        profile_columns = {
            column["name"] for column in inspect(engine).get_columns("farmer_profiles")
        }
        additions = {
            "user_id": "INTEGER",
            "contact_number": "VARCHAR(30)",
            "address": "VARCHAR(500)",
            "latitude": "FLOAT",
            "longitude": "FLOAT",
        }
        with engine.begin() as connection:
            for column_name, column_type in additions.items():
                if column_name not in profile_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE farmer_profiles ADD COLUMN "
                            f"{column_name} {column_type}"
                        )
                    )
            # SQLite supports partial indexes, allowing the legacy unowned
            # profile row(s) to remain NULL while enforcing one profile per
            # authenticated user.
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "uq_farmer_profiles_user_id ON farmer_profiles(user_id) "
                    "WHERE user_id IS NOT NULL"
                )
            )

    db = SessionLocal()
    try:
        # Check if profile already exists, if not seed a default profile
        profile = db.query(FarmerProfile).first()
        if not profile:
            default_profile = FarmerProfile(
                farmer_name="Ramesh Kumar",
                location="Bhatinda, Punjab",
                current_crop="Tomato",
                land_size_hectares=1.5,
                soil_type="Loam",
                ph=6.7,
                irrigation_type="Drip",
                budget="Medium",
                language="en"
            )
            db.add(default_profile)
            db.commit()
    finally:
        db.close()


PASSWORD_HASH_SCHEME = "scrypt"
PASSWORD_SCRYPT_N = 2**14
PASSWORD_SCRYPT_R = 8
PASSWORD_SCRYPT_P = 1
PASSWORD_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hash a password with a per-password salt using the stdlib scrypt KDF."""
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=PASSWORD_SCRYPT_N,
        r=PASSWORD_SCRYPT_R,
        p=PASSWORD_SCRYPT_P,
    )
    return "$".join(
        (
            PASSWORD_HASH_SCHEME,
            str(PASSWORD_SCRYPT_N),
            str(PASSWORD_SCRYPT_R),
            str(PASSWORD_SCRYPT_P),
            salt.hex(),
            digest.hex(),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password without exposing timing differences for a valid hash."""
    try:
        scheme, n, r, p, salt_hex, digest_hex = encoded_hash.split("$")
        if scheme != PASSWORD_HASH_SCHEME:
            return False
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(candidate, bytes.fromhex(digest_hex))
    except (TypeError, ValueError, UnicodeError):
        return False


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db, user: User, ttl_seconds: int) -> str:
    """Create a random cookie token while storing only its SHA-256 digest."""
    token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            token_hash=hash_session_token(token),
            user_id=user.id,
            expires_at=datetime.datetime.utcnow()
            + datetime.timedelta(seconds=ttl_seconds),
        )
    )
    db.commit()
    return token


def user_for_session(db, token: Optional[str]) -> Optional[User]:
    """Resolve a live session token to its user, revoking expired sessions."""
    if not token:
        return None
    session = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == hash_session_token(token),
            UserSession.revoked.is_(False),
        )
        .first()
    )
    if not session:
        return None
    now = datetime.datetime.utcnow()
    if session.expires_at <= now:
        session.revoked = True
        db.commit()
        return None
    return db.query(User).filter(User.id == session.user_id).first()
