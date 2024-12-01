from typing import TypedDict


class UserData(TypedDict):
    zone: str
    user_id: int
    latitude: float
    longitude: float
    reason: str
    photo: str
    gos_number: str
    ya_disk_file_name: str