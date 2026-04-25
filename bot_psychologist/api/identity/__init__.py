"""Public exports for identity layer."""

from .middleware import (
    build_fingerprint_from_request,
    extract_legacy_user_id_from_request,
    generate_session_id,
    mask_external_id,
)
from .models import IdentityContext, LinkedIdentity, SessionRecord, UserRecord
from .repository import IdentityRepository
from .service import IdentityService

__all__ = [
    "IdentityContext",
    "LinkedIdentity",
    "SessionRecord",
    "UserRecord",
    "IdentityRepository",
    "IdentityService",
    "build_fingerprint_from_request",
    "extract_legacy_user_id_from_request",
    "generate_session_id",
    "mask_external_id",
]

