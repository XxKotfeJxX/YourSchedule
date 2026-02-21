from sqlalchemy.orm import Session

from app.domain.models import Company, User
from app.services.auth_service import AuthService


class AuthController:
    def __init__(
        self,
        session: Session,
        auth_service: AuthService | None = None,
    ) -> None:
        self.session = session
        self.auth_service = auth_service or AuthService()

    def has_company_account(self) -> bool:
        return self.auth_service.has_company_account(session=self.session)

    def has_any_account(self) -> bool:
        return self.auth_service.has_any_account(session=self.session)

    def bootstrap_company_account(self, company_name: str, username: str, password: str) -> User:
        return self.auth_service.bootstrap_company_account(
            session=self.session,
            company_name=company_name,
            username=username,
            password=password,
        )

    def register_user(
        self,
        username: str,
        password: str,
        company_name: str | None = None,
    ) -> User:
        return self.auth_service.register_user(
            session=self.session,
            username=username,
            password=password,
            company_name=company_name,
        )

    def authenticate(self, username: str, password: str) -> User | None:
        return self.auth_service.authenticate(
            session=self.session,
            username=username,
            password=password,
        )

    def create_personal_user(
        self,
        company_id: int,
        username: str,
        password: str,
        resource_id: int | None = None,
        subgroup_id: int | None = None,
    ) -> User:
        return self.auth_service.create_personal_user(
            session=self.session,
            company_id=company_id,
            username=username,
            password=password,
            resource_id=resource_id,
            subgroup_id=subgroup_id,
        )

    def list_company_users(self, company_id: int) -> list[User]:
        return self.auth_service.list_company_users(
            session=self.session,
            company_id=company_id,
        )

    def list_available_personal_users_for_company(self, company_id: int) -> list[User]:
        return self.auth_service.list_available_personal_users_for_company(
            session=self.session,
            company_id=company_id,
        )

    def list_group_users(
        self,
        *,
        company_id: int,
        group_id: int,
        subgroup_ids: list[int] | None = None,
    ) -> list[User]:
        return self.auth_service.list_group_users(
            session=self.session,
            company_id=company_id,
            group_id=group_id,
            subgroup_ids=subgroup_ids,
        )

    def update_user_membership(
        self,
        user_id: int,
        *,
        resource_id: int | None,
        subgroup_id: int | None,
    ) -> User:
        return self.auth_service.update_user_membership(
            session=self.session,
            user_id=user_id,
            resource_id=resource_id,
            subgroup_id=subgroup_id,
        )

    def reassign_personal_user_company(self, user_id: int, company_id: int) -> User:
        return self.auth_service.reassign_personal_user_company(
            session=self.session,
            user_id=user_id,
            company_id=company_id,
        )

    def get_company(self, company_id: int) -> Company | None:
        return self.auth_service.get_company(session=self.session, company_id=company_id)
