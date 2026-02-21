from __future__ import annotations

import hashlib
import hmac
import os

from sqlalchemy.orm import Session

from app.domain.enums import UserRole
from app.domain.models import Company, User
from app.repositories.auth_repository import AuthRepository


class AuthService:
    def __init__(self, repository_cls: type[AuthRepository] = AuthRepository) -> None:
        self.repository_cls = repository_cls

    def has_company_account(self, session: Session) -> bool:
        return self.repository_cls(session).any_company_user_exists()

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
        resource_id: int,
    ) -> User:
        repository = self.repository_cls(session)
        return repository.create_user(
            company_id=company_id,
            username=username.strip(),
            password_hash=self._hash_password(password),
            role=UserRole.PERSONAL,
            resource_id=resource_id,
        )

    def list_company_users(self, session: Session, company_id: int) -> list[User]:
        return self.repository_cls(session).list_users_by_company(company_id=company_id)

    def get_company(self, session: Session, company_id: int) -> Company | None:
        return self.repository_cls(session).get_company(company_id=company_id)

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
