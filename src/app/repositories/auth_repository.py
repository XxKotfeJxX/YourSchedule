from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.enums import UserRole
from app.domain.models import Company, User


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_company(self, name: str) -> Company:
        company = Company(name=name)
        self.session.add(company)
        self.session.flush()
        return company

    def get_company(self, company_id: int) -> Company | None:
        return self.session.get(Company, company_id)

    def get_company_by_name(self, name: str) -> Company | None:
        statement = select(Company).where(Company.name == name)
        return self.session.scalars(statement).first()

    def list_companies(self) -> list[Company]:
        statement = select(Company).order_by(Company.name.asc(), Company.id.asc())
        return list(self.session.scalars(statement).all())

    def create_user(
        self,
        company_id: int,
        username: str,
        password_hash: str,
        role: UserRole,
        resource_id: int | None = None,
        subgroup_id: int | None = None,
    ) -> User:
        user = User(
            company_id=company_id,
            username=username,
            password_hash=password_hash,
            role=role,
            resource_id=resource_id,
            subgroup_id=subgroup_id,
            is_active=True,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_user(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_user_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username)
        return self.session.scalars(statement).first()

    def list_users_by_company(self, company_id: int) -> list[User]:
        statement = (
            select(User)
            .where(User.company_id == company_id)
            .order_by(User.role.asc(), User.username.asc())
        )
        return list(self.session.scalars(statement).all())

    def list_personal_users(self) -> list[User]:
        statement = (
            select(User)
            .where(User.role == UserRole.PERSONAL)
            .order_by(User.username.asc(), User.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def company_has_company_user(self, company_id: int) -> bool:
        statement = (
            select(User.id)
            .where(
                User.company_id == company_id,
                User.role == UserRole.COMPANY,
            )
            .limit(1)
        )
        return self.session.scalars(statement).first() is not None

    def list_personal_users_by_group(
        self,
        *,
        company_id: int,
        group_id: int,
        subgroup_ids: list[int] | None = None,
    ) -> list[User]:
        resource_ids = [group_id]
        if subgroup_ids:
            resource_ids.extend(subgroup_ids)
        statement = (
            select(User)
            .where(
                User.company_id == company_id,
                User.role == UserRole.PERSONAL,
                or_(User.resource_id.in_(resource_ids), User.subgroup_id.in_(resource_ids)),
            )
            .order_by(User.username.asc(), User.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def update_user_membership(
        self,
        user_id: int,
        *,
        resource_id: int | None,
        subgroup_id: int | None,
    ) -> User:
        user = self.get_user(user_id)
        if user is None:
            raise ValueError(f"User with id={user_id} was not found")
        user.resource_id = resource_id
        user.subgroup_id = subgroup_id
        self.session.flush()
        return user

    def update_user_company(self, user_id: int, company_id: int) -> User:
        user = self.get_user(user_id)
        if user is None:
            raise ValueError(f"User with id={user_id} was not found")
        user.company_id = company_id
        self.session.flush()
        return user

    def any_user_exists(self) -> bool:
        statement = select(User.id).limit(1)
        return self.session.scalars(statement).first() is not None

    def any_company_user_exists(self) -> bool:
        statement = select(User.id).where(User.role == UserRole.COMPANY).limit(1)
        return self.session.scalars(statement).first() is not None
