"""Pet collection system — gacha-style pet collection with rarity tiers."""


from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid

RARITY_WEIGHTS = {"common": 50, "uncommon": 30, "rare": 15, "legendary": 5}

# --- Leveling economy --------------------------------------------------------
# Pets level by *playing* (chatting with the equipped pet), not only by pulling
# duplicates. XP per chat is small so leveling feels earned over regular use.
MAX_PET_LEVEL = 10
XP_PER_CHAT = 10          # equipped pet gains this each chat turn
XP_PER_DUPLICATE = 50     # duplicate pull still grants the original chunk

# Level milestones that grant a one-time bonus pull (perk for loyalty).
# Reached the *first* time the equipped pet crosses each level.
MILESTONE_PULL_BONUS = {5: 1, 10: 2}

# --- Pity thresholds ---------------------------------------------------------
# Base pity: guarantee a rare at 30 pulls, a legendary at 50. Equipping a
# higher-rarity pet *lowers* these (a real perk for showing off your best pet).
BASE_PITY_RARE = 30
BASE_PITY_LEGENDARY = 50
_PITY_BY_EQUIPPED_RARITY = {
    "rare": (28, 45),
    "legendary": (25, 40),
}


def xp_to_next_level(level: int) -> int:
    """XP required to advance *from* the given level. Matches the historical
    `level * 100` curve (L1→2 = 100, … L9→10 = 900; total L1→10 = 4500)."""
    return level * 100


def apply_pet_xp(pet: "UserPet", amount: int) -> dict[str, int | bool]:
    """Add XP to a pet and roll over level-ups. Single source of truth for the
    leveling math — shared by the chat-XP path and the duplicate-pull path.

    Returns a summary the caller can surface to the UI/SSE: how much XP was
    gained, the resulting level, whether a level-up happened, and the highest
    milestone newly crossed (0 if none) so a bonus pull can be granted once.
    """
    start_level = pet.level
    if pet.level >= MAX_PET_LEVEL:
        # Already maxed — keep XP pinned so the bar reads full, no overflow.
        pet.xp = 0
        return {"xp_gained": 0, "new_level": pet.level, "leveled_up": False, "milestone": 0}

    pet.xp += amount
    while pet.level < MAX_PET_LEVEL and pet.xp >= xp_to_next_level(pet.level):
        pet.xp -= xp_to_next_level(pet.level)
        pet.level += 1
    if pet.level >= MAX_PET_LEVEL:
        pet.xp = 0  # cap: no XP accrues past max level

    milestone = 0
    for level in sorted(MILESTONE_PULL_BONUS):
        if start_level < level <= pet.level:
            milestone = level
    return {
        "xp_gained": amount,
        "new_level": pet.level,
        "leveled_up": pet.level > start_level,
        "milestone": milestone,
    }


def pity_thresholds(equipped_rarity: str | None) -> tuple[int, int]:
    """Return (rare_at, legendary_at) pity thresholds for the equipped rarity."""
    return _PITY_BY_EQUIPPED_RARITY.get(equipped_rarity or "", (BASE_PITY_RARE, BASE_PITY_LEGENDARY))

PET_CATALOG = [
    # Common (8)
    {"id": "sparrow", "name": "Sparrow", "name_zh": "麻雀", "rarity": "common", "description": "A cheerful little companion.", "description_zh": "活潑的小夥伴。"},
    {"id": "pigeon", "name": "Pigeon", "name_zh": "鴿子", "rarity": "common", "description": "Reliable and always on time.", "description_zh": "可靠且準時。"},
    {"id": "robin", "name": "Robin", "name_zh": "知更鳥", "rarity": "common", "description": "Brings good news every morning.", "description_zh": "每天早上帶來好消息。"},
    {"id": "duckling", "name": "Duckling", "name_zh": "小鴨", "rarity": "common", "description": "Follows you everywhere.", "description_zh": "到哪都跟著你。"},
    {"id": "chick", "name": "Chick", "name_zh": "小雞", "rarity": "common", "description": "Tiny but full of energy.", "description_zh": "小小的但充滿活力。"},
    {"id": "hamster", "name": "Hamster", "name_zh": "倉鼠", "rarity": "common", "description": "Hoards snacks like you hoard stocks.", "description_zh": "囤零食就像你囤股票。"},
    {"id": "bunny", "name": "Bunny", "name_zh": "兔子", "rarity": "common", "description": "Quick reflexes for quick trades.", "description_zh": "快速反應適合快速交易。"},
    {"id": "kitten", "name": "Kitten", "name_zh": "小貓", "rarity": "common", "description": "Curious about every chart pattern.", "description_zh": "對每個圖表形態都好奇。"},
    # Uncommon (6)
    {"id": "owl", "name": "Owl", "name_zh": "貓頭鷹", "rarity": "uncommon", "description": "Wise analyst of market trends.", "description_zh": "市場趨勢的智慧分析師。"},
    {"id": "parrot", "name": "Parrot", "name_zh": "鸚鵡", "rarity": "uncommon", "description": "Repeats your best trade strategies.", "description_zh": "重複你最好的交易策略。"},
    {"id": "fox", "name": "Fox", "name_zh": "狐狸", "rarity": "uncommon", "description": "Cunning and sharp-eyed.", "description_zh": "狡猾且眼光銳利。"},
    {"id": "penguin", "name": "Penguin", "name_zh": "企鵝", "rarity": "uncommon", "description": "Cool under market pressure.", "description_zh": "在市場壓力下保持冷靜。"},
    {"id": "corgi", "name": "Corgi", "name_zh": "柯基", "rarity": "uncommon", "description": "Loyal and never leaves your side.", "description_zh": "忠誠且永遠在你身邊。"},
    {"id": "hedgehog", "name": "Hedgehog", "name_zh": "刺蝟", "rarity": "uncommon", "description": "Defensive strategy expert.", "description_zh": "防禦策略專家。"},
    # Rare (4)
    {"id": "eagle", "name": "Eagle", "name_zh": "老鷹", "rarity": "rare", "description": "Sees market opportunities from above.", "description_zh": "從高處看見市場機會。"},
    {"id": "phoenix", "name": "Phoenix", "name_zh": "鳳凰", "rarity": "rare", "description": "Rises from market crashes.", "description_zh": "從市場崩盤中浴火重生。"},
    {"id": "snow_leopard", "name": "Snow Leopard", "name_zh": "雪豹", "rarity": "rare", "description": "Silent and precise in execution.", "description_zh": "沉默且精準執行。"},
    {"id": "dragon", "name": "Dragon", "name_zh": "神龍", "rarity": "rare", "description": "Commands respect in any market.", "description_zh": "在任何市場都令人敬畏。"},
    # Legendary (2)
    {"id": "golden_kestrel", "name": "Golden Kestrel", "name_zh": "黃金紅隼", "rarity": "legendary", "description": "The ultimate trading companion. Legendary foresight.", "description_zh": "終極交易夥伴。傳說中的遠見。"},
    {"id": "cosmic_falcon", "name": "Cosmic Falcon", "name_zh": "宇宙獵鷹", "rarity": "legendary", "description": "Transcends dimensions to find alpha.", "description_zh": "超越維度尋找超額報酬。"},
]


class UserPet(TimestampMixin, Base):
    __tablename__ = "user_pets"
    __table_args__ = (
        Index("ix_user_pet_user", "user_id"),
        Index("ix_user_pet_active", "user_id", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    pet_id: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    obtained_via: Mapped[str] = mapped_column(String(50), default="pull")


class UserPetStats(Base):
    __tablename__ = "user_pet_stats"
    __table_args__ = (Index("ix_pet_stats_user", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    total_pulls: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_login_date: Mapped[str | None] = mapped_column(String(10))
    chat_count: Mapped[int] = mapped_column(Integer, default=0)
    available_pulls: Mapped[int] = mapped_column(Integer, default=1)
    pity_counter: Mapped[int] = mapped_column(Integer, default=0)
