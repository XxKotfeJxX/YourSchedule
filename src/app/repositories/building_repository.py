from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Building


class BuildingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_building(
        self,
        *,
        name: str,
        address: str | None = None,
        company_id: int | None = None,
    ) -> Building:
        building = Building(
            company_id=company_id,
            name=name,
            address=address,
            is_archived=False,
        )
        self.session.add(building)
        self.session.flush()
        return building

    def get_building(self, building_id: int) -> Building | None:
        return self.session.get(Building, building_id)

    def list_buildings(
        self,
        *,
        company_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Building]:
        statement = select(Building).order_by(Building.name.asc(), Building.id.asc())
        if company_id is not None:
            statement = statement.where(Building.company_id == company_id)
        if not include_archived:
            statement = statement.where(Building.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

    def update_building(
        self,
        building_id: int,
        *,
        name: str | None = None,
        address: str | None = None,
        is_archived: bool | None = None,
    ) -> Building:
        building = self.get_building(building_id)
        if building is None:
            raise ValueError(f"Building with id={building_id} was not found")

        if name is not None:
            building.name = name
        if address is not None:
            building.address = address
        if is_archived is not None:
            building.is_archived = is_archived

        self.session.flush()
        return building

    def archive_building(self, building_id: int) -> Building:
        return self.update_building(building_id, is_archived=True)

    def delete_building(self, building_id: int) -> bool:
        building = self.get_building(building_id)
        if building is None:
            return False
        self.session.delete(building)
        self.session.flush()
        return True
