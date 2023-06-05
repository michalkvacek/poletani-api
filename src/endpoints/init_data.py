from database.models import User, Flight, Copilot, Airport, Aircraft
from endpoints.base import BaseEndpoint


class InitDataEndpoint(BaseEndpoint):

    async def on_get(self):
        user_ids = []
        copilot_ids = []
        flight_ids = []

        users = [
            User(avatar_image_url="", name="Karel Vomacka", email="a@test.cz", password_hashed="****"),
            User(avatar_image_url="", name="Karel Novak", email="b@test.cz", password_hashed="****"),
            User(avatar_image_url="", name="Franta Pavel", email="c@test.cz", password_hashed="****"),
        ]

        airport = Airport(name="Letiste Letnany", icao_code="LKLT")
        self.db.add(airport)

        for user in users:
            self.db.add(user)
            await self.db.flush()
            user_ids.append(user.id)

            aircraft = Aircraft(name="OK-AUR28", type="Bristell NG5", description="", created_by=user)
            self.db.add(aircraft)

            copilot = None
            if user.name == 'Franta Pavel':
                copilot = Copilot(name="Copilot test", created_by_id=user.id)
                self.db.add(copilot)
                await self.db.flush()

                copilot_ids.append(copilot.id)

            flight = Flight(name="test flight", description="Testovaci popis", duration_total=65, duration_pic=65,
                            takeoff_airport=airport, landing_airport=airport, aircraft=aircraft, created_by_id=user.id,
                            copilot_id=copilot.id if copilot else None)
            self.db.add(flight)
            await self.db.flush()
            flight_ids.append(flight.id)

        return {
            "user_ids": user_ids,
            "copilot_ids": copilot_ids,
            "flight_ids": flight_ids,
            'airport_id': airport.id
        }

        #
        #
        # self.db.add(Flight(name="test"))
        # await self.db.flush()
        #
        # data = await self.db.execute(select(Flight).order_by(desc(Flight.id)))
        # model = data.scalars().first()
        # return {
        #     "status": model
        # }
