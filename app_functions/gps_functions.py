import requests

def get_address_from_coordinates(latitude, longitude, apikey):
    url = "https://api.geoapify.com/v1/geocode/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "apiKey": apikey,
        "lang": "ru"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        features = data.get("features", [])
        if features:
            return features[0]["properties"]
        return "Адрес не найден"
    return f"Ошибка: {response.status_code}"


def parse_data_from_gps_dict(gps_dict: dict) -> dict:
    """Разбирает полученные от gps библиотеки данные."""
    result = {}
    keys = ['formatted', 'city', 'county', 'district', 'suburb', 'street',
            'housenumber']
    for key in keys:
        result[key] = gps_dict.get(key, f'{key} не найдено')
    return result
