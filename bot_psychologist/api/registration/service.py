"""Business logic for registration and access control."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from api.identity import IdentityService

from .guards import LinkAttemptGuard
from .models import (
    ConfirmLinkResponse,
    InviteKeyCreateResponse,
    LinkCodeResponse,
    LoginResponse,
    RegisterResponse,
    SessionContext,
)
from .repository import RegistrationRepository
from .security import generate_access_key, generate_invite_key, generate_link_code, hash_key, verify_key


logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RegistrationServiceError(Exception):
    """Доменные ошибки registration-сервиса."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RegistrationService:
    """Registration/login/linking use-cases."""

    def __init__(
        self,
        *,
        repository: RegistrationRepository,
        identity_service: IdentityService,
        link_guard: LinkAttemptGuard,
    ) -> None:
        self._repository = repository
        self._identity_service = identity_service
        self._link_guard = link_guard

    async def register(self, *, username: str, invite_key: str) -> RegisterResponse:
        username_norm = username.strip().lower()
        if self._repository.get_profile_by_username(username_norm):
            raise RegistrationServiceError("Username already exists", status_code=409)

        invite = self._repository.get_invite_key(invite_key)
        if not invite:
            raise RegistrationServiceError("Invite key is invalid", status_code=400)
        if int(invite.get("is_active") or 0) != 1 or invite.get("used_at"):
            raise RegistrationServiceError("Invite key is already used", status_code=400)
        expires_raw = str(invite.get("expires_at") or "").strip()
        expires_at = datetime.fromisoformat(expires_raw) if expires_raw else None
        if expires_at is None or expires_at < _utc_now():
            raise RegistrationServiceError("Invite key is expired", status_code=400)

        role = str(invite.get("role_grant") or "user")
        registration_session_id = f"reg_{uuid.uuid4().hex}"
        identity = await self._identity_service.resolve_or_create(
            provider="api",
            external_id=f"registered:{username_norm}",
            session_id=registration_session_id,
            channel="api",
            metadata={"source": "registration"},
        )

        plain_access_key = generate_access_key()
        hashed_access_key = hash_key(plain_access_key)
        self._repository.create_user_profile(
            user_id=identity.user_id,
            username=username_norm,
            hashed_access_key=hashed_access_key,
            role=role,
        )

        consumed = self._repository.consume_invite_key(invite_key, identity.user_id)
        if not consumed:
            raise RegistrationServiceError("Invite key could not be consumed", status_code=409)

        logger.info("registration.user_created user_id=%s role=%s", identity.user_id, role)
        return RegisterResponse(user_id=identity.user_id, access_key=plain_access_key, role=role)

    async def login(self, *, username: str, access_key: str) -> LoginResponse:
        username_norm = username.strip().lower()
        profile = self._repository.get_profile_by_username(username_norm)
        if not profile:
            raise RegistrationServiceError("Invalid username or access key", status_code=401)

        if int(profile.get("is_active") or 0) != 1:
            raise RegistrationServiceError("User is inactive", status_code=403)
        if int(profile.get("is_blocked") or 0) == 1 or str(profile.get("role") or "") == "blocked":
            raise RegistrationServiceError("User is blocked", status_code=403)

        hashed_access_key = str(profile.get("hashed_access_key") or "")
        if not verify_key(access_key, hashed_access_key):
            raise RegistrationServiceError("Invalid username or access key", status_code=401)

        session = self._repository.create_session(
            user_id=str(profile["user_id"]),
            username=username_norm,
            role=str(profile.get("role") or "user"),
        )
        return LoginResponse(
            user_id=session.user_id,
            session_token=session.session_token,
            role=session.role,
            username=session.username,
            expires_at=session.expires_at,
        )

    async def resolve_session_context(self, session_token: str) -> Optional[SessionContext]:
        token = session_token.strip()
        if not token:
            return None
        return self._repository.get_session(token)

    async def create_link_code(self, *, session_token: str) -> LinkCodeResponse:
        session = self._repository.get_session(session_token)
        if session is None:
            raise RegistrationServiceError("Session is invalid or expired", status_code=401)

        code = generate_link_code()
        self._repository.create_link_code(user_id=session.user_id, code=code, ttl_seconds=900)
        return LinkCodeResponse(code=code, expires_in_seconds=900)

    async def confirm_telegram_link(
        self,
        *,
        code: str,
        telegram_user_id: str,
    ) -> ConfirmLinkResponse:
        code_norm = code.strip().upper()
        telegram_norm = telegram_user_id.strip()
        if not code_norm or not telegram_norm:
            return ConfirmLinkResponse(ok=False, error_message="Некорректный код или user id")

        blocked = await self._link_guard.is_blocked(telegram_norm)
        if blocked:
            return ConfirmLinkResponse(
                ok=False,
                error_message="Слишком много попыток. Попробуйте через 15 минут.",
            )

        status, code_data = self._repository.get_link_code_status(code_norm)
        if status != "valid" or not code_data:
            await self._link_guard.check_and_record(telegram_norm, success=False)
            if status == "expired":
                return ConfirmLinkResponse(ok=False, error_message="Код истёк")
            if status == "used":
                return ConfirmLinkResponse(ok=False, error_message="Код уже использован")
            return ConfirmLinkResponse(ok=False, error_message="Код недействителен")

        user_id = str(code_data["user_id"])
        try:
            await self._identity_service.link_identity(
                user_id=user_id,
                provider="telegram",
                external_id=telegram_norm,
                metadata={"source": "telegram_link_code"},
            )
        except Exception as exc:
            logger.warning("registration.link_identity_failed user_id=%s err=%s", user_id, exc)
            await self._link_guard.check_and_record(telegram_norm, success=False)
            return ConfirmLinkResponse(ok=False, error_message="Не удалось привязать Telegram")

        self._repository.mark_link_code_used(code_norm, telegram_norm)
        await self._link_guard.check_and_record(telegram_norm, success=True)

        profile = self._repository.get_profile_by_user_id(user_id)
        username = str(profile.get("username") or "") if profile else None
        return ConfirmLinkResponse(ok=True, user_id=user_id, username=username)

    async def create_invite_key(
        self,
        *,
        admin_session_token: str,
        role_grant: str,
        expires_in_days: int,
    ) -> InviteKeyCreateResponse:
        session = self._repository.get_session(admin_session_token)
        if session is None:
            raise RegistrationServiceError("Session is invalid or expired", status_code=401)
        if session.role != "admin":
            raise RegistrationServiceError("Admin role required", status_code=403)

        key_value = generate_invite_key()
        expires_at = _utc_now() + timedelta(days=max(1, int(expires_in_days)))
        self._repository.create_invite_key(
            key_value=key_value,
            role_grant=role_grant,
            expires_at=expires_at,
            created_by=session.user_id,
        )
        return InviteKeyCreateResponse(key_value=key_value, expires_at=expires_at)
