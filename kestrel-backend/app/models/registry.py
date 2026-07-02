"""Single import point that registers every ORM model with Base.metadata.

Both runtime table creation (app.db.session.create_tables) and Alembic
(alembic/env.py) import this so the full schema is always visible from one place
— no drift between what the app creates and what migrations see.
"""

# Importing these modules has the side effect of registering their mapped
# classes on Base.metadata. Keep this list complete.
import app.agent.alerts.models  # noqa: F401
import app.agent.hooks.feedback_loop  # noqa: F401
import app.agent.memory.episodic  # noqa: F401
import app.agent.memory.semantic  # noqa: F401
import app.agent.observe  # noqa: F401
import app.agent.sessions.models  # noqa: F401
import app.channels.models  # noqa: F401
import app.models.alert  # noqa: F401
import app.models.pet  # noqa: F401
import app.models.portfolio  # noqa: F401
import app.models.user  # noqa: F401
import app.models.watchlist  # noqa: F401
from app.models.base import Base

# Re-exported for callers that want the metadata object.
metadata = Base.metadata

__all__ = ["Base", "metadata"]
