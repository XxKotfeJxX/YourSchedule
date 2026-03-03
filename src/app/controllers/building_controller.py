from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.models import Building
from app.repositories.building_repository import BuildingRepository


class BuildingController:
    def __init__(self, session: Session) -> None:
        self.repository = BuildingRepository(session=session)

    def create_building(
        self,
        *,
        name: str,
        address: str | None = None,
        company_id: int | None = None,
    ) -> Building:
        return self.repository.create_building(
            name=name,
            address=address,
            company_id=company_id,
        )

    def get_building(self, building_id: int) -> Building | None:
        return self.repository.get_building(building_id)

    def list_buildings(
        self,
        *,
        company_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Building]:
        return self.repository.list_buildings(
            company_id=company_id,
            include_archived=include_archived,
        )

    def update_building(
        self,
        building_id: int,
        *,
        name: str | None = None,
        address: str | None = None,
        is_archived: bool | None = None,
    ) -> Building:
        return self.repository.update_building(
            building_id,
            name=name,
            address=address,
            is_archived=is_archived,
        )

    def archive_building(self, building_id: int) -> Building:
        return self.repository.archive_building(building_id)

    def delete_building(self, building_id: int) -> bool:
        return self.repository.delete_building(building_id)
