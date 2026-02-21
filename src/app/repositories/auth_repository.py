from sqlalchemy import select
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
    ) -> User:
        user = User(
            company_id=company_id,
            username=username,
            password_hash=password_hash,
            role=role,
            resource_id=resource_id,
            is_active=True,
        )
        self.session.add(user)
        self.session.flush()
        return user

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

    def any_company_user_exists(self) -> bool:
        statement = select(User.id).where(User.role == UserRole.COMPANY).limit(1)
        return self.session.scalars(statement).first() is not None
