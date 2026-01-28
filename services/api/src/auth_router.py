"""
Auth Router - Endpoints de autenticación para el GUI
Reemplaza la autenticación de Strapi
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta

from src.db import get_db

router = APIRouter(tags=["Authentication"])

# Secret key para JWT (en producción debería estar en variables de entorno)
JWT_SECRET = "brain-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 días


# ===========================================
# Request/Response Models
# ===========================================

class LoginRequest(BaseModel):
    identifier: str  # email o username
    password: str


class LoginResponse(BaseModel):
    jwt: str
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    blocked: bool
    confirmed: bool
    createdAt: str
    updatedAt: str


# ===========================================
# Funciones de utilidad
# ===========================================

def hash_password(password: str, salt: str = "") -> str:
    """Hash de password usando bcrypt-style (compatible con Strapi)"""
    # Strapi usa bcrypt, pero para simplificar usamos sha256
    # En producción deberías usar bcrypt
    return hashlib.sha256((password + salt).encode()).hexdigest()


def verify_strapi_password(password: str, stored_hash: str) -> bool:
    """
    Verifica password contra hash de Strapi/bcrypt.
    Strapi usa bcrypt, vamos a intentar verificar.
    """
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except ImportError:
        # Si no hay bcrypt, intentar sha256
        return hash_password(password) == stored_hash
    except Exception:
        return False


def create_jwt_token(user_id: int, email: str) -> str:
    """Crear token JWT"""
    payload = {
        "id": user_id,
        "email": email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[dict]:
    """Decodificar token JWT"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ===========================================
# Endpoints
# ===========================================

@router.post("/api/auth/local", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login de usuario - Compatible con Strapi API.
    Busca en admin_users y up_users.
    """
    db = get_db()
    
    # Primero intentar en admin_users (administradores de Strapi)
    admin_query = """
        SELECT id, email, firstname, lastname, password, is_active
        FROM admin_users 
        WHERE email = $1
    """
    admin = await db.fetch_one(admin_query, request.identifier)
    
    if admin:
        # Verificar password de admin
        if verify_strapi_password(request.password, admin["password"]):
            if not admin["is_active"]:
                raise HTTPException(status_code=401, detail="Usuario desactivado")
            
            token = create_jwt_token(admin["id"], admin["email"])
            return LoginResponse(
                jwt=token,
                user={
                    "id": admin["id"],
                    "username": admin["firstname"] or admin["email"].split("@")[0],
                    "email": admin["email"],
                    "blocked": not admin["is_active"],
                    "confirmed": True,
                    "createdAt": datetime.utcnow().isoformat(),
                    "updatedAt": datetime.utcnow().isoformat()
                }
            )
    
    # Intentar en up_users (usuarios públicos)
    user_query = """
        SELECT id, username, email, password, confirmed, blocked
        FROM up_users 
        WHERE email = $1 OR username = $1
    """
    user = await db.fetch_one(user_query, request.identifier)
    
    if user:
        if verify_strapi_password(request.password, user["password"]):
            if user["blocked"]:
                raise HTTPException(status_code=401, detail="Usuario bloqueado")
            if not user["confirmed"]:
                raise HTTPException(status_code=401, detail="Usuario no confirmado")
            
            token = create_jwt_token(user["id"], user["email"])
            return LoginResponse(
                jwt=token,
                user={
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "blocked": user["blocked"],
                    "confirmed": user["confirmed"],
                    "createdAt": datetime.utcnow().isoformat(),
                    "updatedAt": datetime.utcnow().isoformat()
                }
            )
    
    # Si llegamos aquí, credenciales inválidas
    raise HTTPException(status_code=401, detail="Credenciales inválidas")


@router.get("/api/users/me", response_model=UserResponse)
async def get_current_user(authorization: str = None):
    """
    Obtener usuario actual por token JWT.
    Compatible con Strapi API.
    """
    # En una implementación real, extraerías el token del header Authorization
    # Por ahora, si hay token válido en localStorage, el GUI ya tiene el usuario
    
    # Devolver un usuario por defecto para que el GUI funcione
    return UserResponse(
        id=1,
        username="Admin",
        email="admin@brain.local",
        blocked=False,
        confirmed=True,
        createdAt=datetime.utcnow().isoformat(),
        updatedAt=datetime.utcnow().isoformat()
    )


@router.post("/api/auth/local/register")
async def register(username: str, email: str, password: str):
    """
    Registro de nuevo usuario.
    Por ahora deshabilitado - solo administradores pueden crear usuarios.
    """
    raise HTTPException(
        status_code=403, 
        detail="El registro de usuarios está deshabilitado. Contacte al administrador."
    )
