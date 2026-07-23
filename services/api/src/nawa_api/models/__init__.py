"""Import every model module so all tables register on the shared Base.metadata.

Required before Alembic autogenerate/`Base.metadata.create_all` runs, since
several tables reference each other by string FK name across modules.
"""

from nawa_api.models import (  # noqa: F401
    ai,
    community,
    identity,
    intake,
    journey,
    profiles,
    programs,
    reports,
)
from nawa_api.models.base import Base  # noqa: F401
