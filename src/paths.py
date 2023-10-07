PHOTO_BASE_PATH = ""
AIRCRAFT_BASE_PATH = ""
FLIGHT_BASE_PATH = ""

def get_photo_basepath(flight_id: int) -> str:
    return f"/app/uploads/photos/{flight_id}"
