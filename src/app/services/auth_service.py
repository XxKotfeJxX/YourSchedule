from __future__ import annotations

import hashlib
import hmac
import os

from sqlalchemy.orm import Session

from app.domain.enums import UserRole
from app.domain.models import Company, CompanyProfile, User
from app.repositories.auth_repository import AuthRepository


class AuthService:
    ALLOWED_THEMES = {"ocean", "graphite", "sunrise", "aurora", "sand", "berry"}

    def __init__(self, repository_cls: type[AuthRepository] = AuthRepository) -> None:
        self.repository_cls = repository_cls

    def has_company_account(self, session: Session) -> bool:
        return self.repository_cls(session).any_company_user_exists()

    def has_any_account(self, session: Session) -> bool:
        return self.repository_cls(session).any_user_exists()

    def bootstrap_company_account(
        self,
        session: Session,
        company_name: str,
        username: str,
        password: str,
    ) -> User:
        repository = self.repository_cls(session)
        company = repository.create_company(name=company_name.strip())
        return repository.create_user(
            company_id=company.id,
            username=username.strip(),
            password_hash=self._hash_password(password),
            role=UserRole.COMPANY,
        )

    def register_user(
        self,
        session: Session,
        username: str,
        password: str,
        company_name: str | None = None,
    ) -> User:
        cleaned_username = username.strip()
        cleaned_company_name = (company_name or "").strip()
        repository = self.repository_cls(session)

        if cleaned_company_name:
            company = repository.create_company(name=cleaned_company_name)
            return repository.create_user(
                company_id=company.id,
                username=cleaned_username,
                password_hash=self._hash_password(password),
                role=UserRole.COMPANY,
            )

        base_name = f"Особистий-{cleaned_username}"
        candidate_name = base_name
        suffix = 2
        while repository.get_company_by_name(candidate_name) is not None:
            candidate_name = f"{base_name}-{suffix}"
            suffix += 1

        company = repository.create_company(name=candidate_name)
        return repository.create_user(
            company_id=company.id,
            username=cleaned_username,
            password_hash=self._hash_password(password),
            role=UserRole.PERSONAL,
            resource_id=None,
            subgroup_id=None,
        )

    def authenticate(self, session: Session, username: str, password: str) -> User | None:
        repository = self.repository_cls(session)
        user = repository.get_user_by_username(username.strip())
        if user is None or not user.is_active:
            return None
        if not self._verify_password(password, user.password_hash):
            return None
        return user

    def create_personal_user(
        self,
        session: Session,
        company_id: int,
        username: str,
        password: str,
        resource_id: int | None = None,
        subgroup_id: int | None = None,
    ) -> User:
        repository = self.repository_cls(session)
        return repository.create_user(
            company_id=company_id,
            username=username.strip(),
            password_hash=self._hash_password(password),
            role=UserRole.PERSONAL,
            resource_id=resource_id,
            subgroup_id=subgroup_id,
        )

    def list_company_users(self, session: Session, company_id: int) -> list[User]:
        return self.repository_cls(session).list_users_by_company(company_id=company_id)

    def list_available_personal_users_for_company(self, session: Session, company_id: int) -> list[User]:
        repository = self.repository_cls(session)
        users = repository.list_personal_users()
        available: list[User] = []
        company_has_owner_cache: dict[int, bool] = {}

        for user in users:
            if user.company_id == company_id:
                available.append(user)
                continue

            if user.resource_id is not None or user.subgroup_id is not None:
                continue

            has_owner = company_has_owner_cache.get(user.company_id)
            if has_owner is None:
                has_owner = repository.company_has_company_user(user.company_id)
                company_has_owner_cache[user.company_id] = has_owner

            # Personal accounts created outside a company are isolated in
            # personal-only companies and can be attached to a company later.
            if not has_owner:
                available.append(user)

        return available

    def list_group_users(
        self,
        session: Session,
        *,
        company_id: int,
        group_id: int,
        subgroup_ids: list[int] | None = None,
    ) -> list[User]:
        return self.repository_cls(session).list_personal_users_by_group(
            company_id=company_id,
            group_id=group_id,
            subgroup_ids=subgroup_ids,
        )

    def get_company(self, session: Session, company_id: int) -> Company | None:
        return self.repository_cls(session).get_company(company_id=company_id)

    def get_company_profile(self, session: Session, company_id: int) -> CompanyProfile:
        return self.repository_cls(session).get_or_create_company_profile(company_id=company_id)

    def update_company_profile(
        self,
        session: Session,
        company_id: int,
        *,
        company_name: str,
        timezone: str,
        theme: str,
        language: str | None = None,
        logo_path: str | None = None,
        update_logo_path: bool = False,
    ) -> tuple[Company, CompanyProfile]:
        cleaned_name = company_name.strip()
        cleaned_timezone = timezone.strip()
        cleaned_theme = theme.strip().lower()
        cleaned_language = language.strip().lower() if language is not None else None
        if not cleaned_name:
            raise ValueError("Назва компанії обов'язкова.")
        if not cleaned_timezone:
            raise ValueError("Часовий пояс обов'язковий.")
        if cleaned_theme not in self.ALLOWED_THEMES:
            raise ValueError("Невідома тема оформлення.")
        if cleaned_language is not None and not cleaned_language:
            raise ValueError("Мова інтерфейсу обов'язкова.")

        repository = self.repository_cls(session)
        company = repository.update_company_name(company_id=company_id, name=cleaned_name)
        profile = repository.update_company_profile(
            company_id=company_id,
            timezone=cleaned_timezone,
            theme=cleaned_theme,
            language=cleaned_language,
            update_language=cleaned_language is not None,
            logo_path=logo_path,
            update_logo_path=update_logo_path,
        )
        return company, profile

    def update_user_membership(
        self,
        session: Session,
        user_id: int,
        *,
        resource_id: int | None,
        subgroup_id: int | None,
    ) -> User:
        return self.repository_cls(session).update_user_membership(
            user_id,
            resource_id=resource_id,
            subgroup_id=subgroup_id,
        )

    def reassign_personal_user_company(
        self,
        session: Session,
        user_id: int,
        company_id: int,
    ) -> User:
        repository = self.repository_cls(session)
        user = repository.get_user(user_id)
        if user is None:
            raise ValueError(f"User with id={user_id} was not found")
        if user.role != UserRole.PERSONAL:
            raise ValueError("Only personal users can be reassigned to a company")
        return repository.update_user_company(user_id=user_id, company_id=company_id)

    def _hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        iterations = 120_000
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            scheme, iterations_text, salt_hex, digest_hex = stored_hash.split("$", maxsplit=3)
            if scheme != "pbkdf2_sha256":
                return False
            iterations = int(iterations_text)
            salt = bytes.fromhex(salt_hex)
            expected_digest = bytes.fromhex(digest_hex)
        except (ValueError, TypeError):
            return False

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual_digest, expected_digest)
