from sqlalchemy import select, desc

from database.models import Flight
from endpoints.base import BaseEndpoint


class FlightsEndpoint(BaseEndpoint):

    async def resolve(self):
        self.db.add(Flight(name="test"))
        await self.db.flush()

        data = await self.db.execute(select(Flight).order_by(desc(Flight.id)))
        model = data.scalars().first()
        return {
            "status": model
        }
