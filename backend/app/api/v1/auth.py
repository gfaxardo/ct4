"""
Endpoint de autenticación - Proxy a API externa de Yego
"""
import httpx
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

# URL de la API de autenticación externa
YEGO_AUTH_URL = "https://api-int.yego.pro/api/auth/login"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    name: str
    role: str
    moduleId: Optional[int] = None
    active: bool
    lastLogin: Optional[str] = None


class LoginResponse(BaseModel):
    accessToken: str
    user: UserResponse


class ErrorResponse(BaseModel):
    error: str
    message: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Autentica usuario contra la API de Yego.
    Actúa como proxy para evitar CORS y centralizar la autenticación.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                YEGO_AUTH_URL,
                json={
                    "username": request.username,
                    "password": request.password
                },
                headers={
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Credenciales incorrectas"
                )
            
            if response.status_code != 200:
                logger.error(f"Error en auth API: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Error en el servicio de autenticación"
                )
            
            data = response.json()
            
            return LoginResponse(
                accessToken=data["accessToken"],
                user=UserResponse(
                    id=data["user"]["id"],
                    username=data["user"]["username"],
                    email=data["user"]["email"],
                    name=data["user"]["name"],
                    role=data["user"]["role"],
                    moduleId=data["user"].get("moduleId"),
                    active=data["user"]["active"],
                    lastLogin=data["user"].get("lastLogin")
                )
            )
            
    except httpx.TimeoutException:
        logger.error("Timeout conectando a API de autenticación")
        raise HTTPException(
            status_code=504,
            detail="Timeout conectando al servicio de autenticación"
        )
    except httpx.RequestError as e:
        logger.error(f"Error de conexión a API de autenticación: {e}")
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar al servicio de autenticación"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en login: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )
