from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
import httpx
from pydantic import BaseModel
from typing import Optional
import secrets

from config import EnvConfig



app_login = FastAPI()

# Состояние для предотвращения CSRF
state_storage = {}
config = EnvConfig(".env")

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserInfo(BaseModel):
    id: int
    uuid: str
    login: str
    display_login: Optional[str] = None
    distributor: str
    distributor_id: Optional[str] = None


@app_login.get("/")
async def home():
    # Ссылка для авторизации
    state = secrets.token_urlsafe(16)
    state_storage[state] = True
    auth_url = (
        f"{config.AUTHORIZE_URL}?client_id={config.get("CLIENT_ID")}&redirect_uri={config.get("REDIRECT_URI")}&scope=&"
        f"response_type=code&state={state}"
    )
    return RedirectResponse(auth_url)


@app_login.get("/code")
async def get_code(code: str, state: str):
    # Проверяем состояние для защиты от CSRF
    if state not in state_storage:
        raise HTTPException(status_code=400, detail="Invalid state")
    del state_storage[state]

    # Обмен кода на токены
    async with httpx.AsyncClient() as client:
        response = await client.post(
            config.TOKEN_URL,
            data={
                "client_id": config.get("CLIENT_ID"),
                "client_secret": config.get("CLIENT_SECRET"),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": config.get("REDIRECT_URI"),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    token_data = response.json()
    return TokenResponse(**token_data)


@app_login.post("/refresh_token")
async def refresh_token(refresh_token: str):
    # Обновление токена
    async with httpx.AsyncClient() as client:
        response = await client.post(
            config.TOKEN_URL,
            data={
                "client_id": config.get("CLIENT_ID"),
                "client_secret": config.get("CLIENT_SECRET"),
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": "",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    token_data = response.json()
    return TokenResponse(**token_data)


@app_login.get("/user_info")
async def user_info(access_token: str):
    # Запрос информации о пользователе
    async with httpx.AsyncClient() as client:
        response = await client.get(
            config.USER_INFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    user_data = response.json()
    return UserInfo(**user_data)
