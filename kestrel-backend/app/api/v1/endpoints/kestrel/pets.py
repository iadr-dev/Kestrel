"""Pet collection system endpoints — gacha pull, equip, collection, progress."""

import random
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.dependencies import get_current_user_id, is_admin_email
from app.models.pet import (
    MILESTONE_PULL_BONUS,
    PET_CATALOG,
    RARITY_WEIGHTS,
    XP_PER_DUPLICATE,
    UserPet,
    UserPetStats,
    apply_pet_xp,
    pity_thresholds,
)
from app.schemas.pets import (
    ActivePetResponse,
    PetCatalogResponse,
    PetEquipResponse,
    PetProgressResponse,
    PetPullResult,
    UserPetListResponse,
)

router = APIRouter(prefix="/user/pets", tags=["Pets"])


def _is_admin(user_id: str, db_user_email: str | None = None) -> bool:
    return is_admin_email(db_user_email)


async def _get_user_email(user_id: str, db: AsyncSession) -> str | None:
    from app.models.user import User
    user = await db.get(User, user_id)
    return user.email if user else None


async def _ensure_stats(user_id: str, db: AsyncSession) -> UserPetStats:
    stmt = select(UserPetStats).where(UserPetStats.user_id == user_id)
    result = await db.execute(stmt)
    stats = result.scalar_one_or_none()
    if not stats:
        stats = UserPetStats(user_id=user_id, available_pulls=1)
        db.add(stats)
        await db.flush()
    return stats


async def _get_equipped_rarity(user_id: str, db: AsyncSession) -> str | None:
    """Rarity of the user's currently equipped pet (drives pity perk), or None."""
    stmt = select(UserPet.pet_id).where(UserPet.user_id == user_id, UserPet.is_active == True)  # noqa: E712
    pet_id = (await db.execute(stmt)).scalar_one_or_none()
    if not pet_id:
        return None
    catalog_map = {p["id"]: p for p in PET_CATALOG}
    pet = catalog_map.get(pet_id)
    return pet["rarity"] if pet else None


async def _ensure_admin_pets(user_id: str, db: AsyncSession) -> None:
    """Give admin all pets at max level. Ensure one is active."""
    stmt = select(UserPet).where(UserPet.user_id == user_id)
    result = await db.execute(stmt)
    existing = {p.pet_id: p for p in result.scalars().all()}

    for pet in PET_CATALOG:
        if pet["id"] not in existing:
            db.add(UserPet(
                user_id=user_id,
                pet_id=pet["id"],
                level=10,
                xp=9999,
                obtained_via="admin",
                is_active=(pet["id"] == "golden_kestrel"),
            ))

    # If no pet is active, activate golden_kestrel
    has_active = any(p.is_active for p in existing.values())
    if not has_active and "golden_kestrel" in existing:
        existing["golden_kestrel"].is_active = True

    await db.flush()


@router.get("/catalog", response_model=PetCatalogResponse)
async def get_catalog() -> dict[str, Any]:
    """Get all available pets with rarity info."""
    return {
        "data": PET_CATALOG,
        "count": len(PET_CATALOG),
        "rarity_weights": RARITY_WEIGHTS,
    }


@router.get("", response_model=UserPetListResponse)
async def get_my_pets(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get user's collected pets."""
    email = await _get_user_email(user_id, db)
    if is_admin_email(email):
        await _ensure_admin_pets(user_id, db)

    stmt = select(UserPet).where(UserPet.user_id == user_id).order_by(UserPet.is_active.desc(), UserPet.created_at)
    result = await db.execute(stmt)
    pets = result.scalars().all()

    catalog_map = {p["id"]: p for p in PET_CATALOG}
    return {
        "data": [
            {
                **catalog_map.get(p.pet_id, {}),
                "id": p.id,
                "pet_id": p.pet_id,
                "is_active": p.is_active,
                "level": p.level,
                "xp": p.xp,
                "obtained_via": p.obtained_via,
                "obtained_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in pets
        ],
        "count": len(pets),
        "total_available": len(PET_CATALOG),
    }


@router.get("/active", response_model=ActivePetResponse)
async def get_active_pet(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get currently equipped pet."""
    email = await _get_user_email(user_id, db)
    if is_admin_email(email):
        await _ensure_admin_pets(user_id, db)

    stmt = select(UserPet).where(UserPet.user_id == user_id, UserPet.is_active == True)  # noqa: E712
    result = await db.execute(stmt)
    active = result.scalar_one_or_none()

    if not active:
        return {"data": None}

    catalog_map = {p["id"]: p for p in PET_CATALOG}
    pet_info = catalog_map.get(active.pet_id, {})
    return {
        "data": {
            "id": active.id,
            "pet_id": active.pet_id,
            "level": active.level,
            "xp": active.xp,
            **pet_info,
        }
    }


@router.put("/{pet_record_id}/equip", response_model=PetEquipResponse)
async def equip_pet(
    pet_record_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Set a pet as active (unequip others). Atomic — no race condition."""
    from fastapi import HTTPException

    # Verify pet exists and belongs to user
    pet = await db.get(UserPet, pet_record_id)
    if not pet or pet.user_id != user_id:
        raise HTTPException(status_code=404, detail="Pet not found")

    # Atomic: deactivate all others, activate this one
    await db.execute(
        update(UserPet)
        .where(UserPet.user_id == user_id, UserPet.id != pet_record_id)
        .values(is_active=False)
    )
    await db.execute(
        update(UserPet)
        .where(UserPet.user_id == user_id, UserPet.id == pet_record_id)
        .values(is_active=True)
    )
    await db.flush()
    return {"status": "equipped", "pet_id": pet.pet_id}


@router.get("/progress", response_model=PetProgressResponse)
async def get_progress(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get pull progress — milestones, streak, available pulls, collection status."""
    stats = await _ensure_stats(user_id, db)
    email = await _get_user_email(user_id, db)
    available = 99 if is_admin_email(email) else stats.available_pulls

    # Pity thresholds reflect the equipped pet's rarity perk (lower = better).
    equipped_rarity = await _get_equipped_rarity(user_id, db)
    pity_rare_at, pity_legendary_at = pity_thresholds(equipped_rarity)

    # Distinct pets collected vs catalog size (drives the 20/20 completion badge).
    distinct_stmt = select(func.count(func.distinct(UserPet.pet_id))).where(UserPet.user_id == user_id)
    collected = (await db.execute(distinct_stmt)).scalar() or 0
    total_pets = len(PET_CATALOG)

    return {
        "streak_days": stats.streak_days,
        "chat_count": stats.chat_count,
        "total_pulls": stats.total_pulls,
        "available_pulls": available,
        "pity_counter": stats.pity_counter,
        "pity_rare_at": pity_rare_at,
        "pity_legendary_at": pity_legendary_at,
        "next_chat_milestone": ((stats.chat_count // 50) + 1) * 50,
        "next_streak_milestone": ((stats.streak_days // 7) + 1) * 7,
        "collected_count": collected,
        "total_pets": total_pets,
        "collection_complete": collected >= total_pets,
    }


@router.post("/pull", response_model=PetPullResult)
async def pull_pet(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Gacha pull — random pet based on rarity weights."""
    stats = await _ensure_stats(user_id, db)
    email = await _get_user_email(user_id, db)
    is_admin = is_admin_email(email)
    if not is_admin and stats.available_pulls <= 0:
        return {"status": "no_pulls", "message": "No available pulls. Keep chatting or maintain your login streak!"}

    # Pity system: guarantee rare/legendary after N pulls. Equipping a higher
    # rarity pet lowers these thresholds (a perk for showing off your best pet).
    equipped_rarity = await _get_equipped_rarity(user_id, db)
    pity_rare_at, pity_legendary_at = pity_thresholds(equipped_rarity)
    stats.pity_counter += 1
    forced_rarity = None
    if stats.pity_counter >= pity_legendary_at:
        forced_rarity = "legendary"
    elif stats.pity_counter >= pity_rare_at:
        forced_rarity = "rare"

    # Weighted random selection (filtered by forced rarity if pity triggers)
    pool: list[dict[str, Any]] = []
    for pet in PET_CATALOG:
        if forced_rarity and pet["rarity"] != forced_rarity:
            continue
        weight = RARITY_WEIGHTS[pet["rarity"]]
        pool.extend([pet] * weight)
    selected = random.choice(pool)

    # Reset pity counter on rare or legendary pull
    if selected["rarity"] in ("rare", "legendary"):
        stats.pity_counter = 0

    # Check if already owned
    stmt = select(UserPet).where(UserPet.user_id == user_id, UserPet.pet_id == selected["id"])
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Duplicate → grant XP via the shared leveling helper (same math as chat)
        xp = apply_pet_xp(existing, XP_PER_DUPLICATE)
        # Crossing a level milestone grants a one-time bonus pull (any XP source)
        milestone = int(xp["milestone"])
        if milestone:
            stats.available_pulls += MILESTONE_PULL_BONUS.get(milestone, 0)
        if not is_admin:
            stats.available_pulls -= 1
        stats.total_pulls += 1
        await db.flush()
        return {
            "status": "duplicate",
            "pet": selected,
            "xp_gained": XP_PER_DUPLICATE,
            "new_level": existing.level,
            "leveled_up": xp["leveled_up"],
            "milestone": milestone,
        }

    # New pet
    is_first = (await db.execute(select(UserPet).where(UserPet.user_id == user_id))).scalars().first() is None
    new_pet = UserPet(
        user_id=user_id,
        pet_id=selected["id"],
        is_active=is_first,
        obtained_via="pull",
    )
    db.add(new_pet)
    if not is_admin:
        stats.available_pulls -= 1
    stats.total_pulls += 1
    await db.flush()

    return {
        "status": "new",
        "pet": selected,
        "record_id": new_pet.id,
        "is_active": new_pet.is_active,
    }
