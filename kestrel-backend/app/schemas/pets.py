from typing import Any

from pydantic import BaseModel, Field


class PetCatalogItem(BaseModel):
    id: str
    name: str
    name_zh: str | None = None
    rarity: str
    description: str | None = None
    photo_url: str | None = None


class PetCatalogResponse(BaseModel):
    data: list[PetCatalogItem] = Field(default_factory=list)
    count: int = 0
    rarity_weights: dict[str, float] = Field(default_factory=dict)


class UserPetItem(BaseModel):
    id: str
    pet_id: str
    name: str | None = None
    name_zh: str | None = None
    rarity: str | None = None
    is_active: bool = False
    level: int = 1
    xp: int = 0
    obtained_via: str | None = None
    obtained_at: str | None = None


class UserPetListResponse(BaseModel):
    data: list[UserPetItem] = Field(default_factory=list)
    count: int = 0
    total_available: int = 0


class ActivePetResponse(BaseModel):
    data: UserPetItem | None = None


class PetEquipResponse(BaseModel):
    status: str
    pet_id: str


class PetProgressResponse(BaseModel):
    streak_days: int = 0
    chat_count: int = 0
    total_pulls: int = 0
    available_pulls: int = 0
    pity_counter: int = 0
    pity_rare_at: int = 30
    pity_legendary_at: int = 50
    next_chat_milestone: int = 50
    next_streak_milestone: int = 7
    collected_count: int = 0
    total_pets: int = 0
    collection_complete: bool = False


class PetPullResult(BaseModel):
    model_config = {"extra": "allow"}

    status: str
    pet: dict[str, Any] | None = None
    is_new: bool = False
    is_pity: bool = False
    is_active: bool = False
    record_id: str | None = None
    xp_gained: int | None = None
    new_level: int | None = None
    leveled_up: bool = False
    milestone: int | None = None
    message: str | None = None
