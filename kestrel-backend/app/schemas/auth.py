from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
    state: str


class RegisterResponse(BaseModel):
    message: str
    user_id: str


class UserMeResponse(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None
    picture_url: str | None = None
    tier: str = "free"
    providers: list[str] | None = None
    is_admin: bool = False
