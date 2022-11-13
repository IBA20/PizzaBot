import requests
import os
from geopy import distance


def fetch_coordinates(address, apikey=os.getenv('YANDEX_GEOCODER_APIKEY')):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(
        base_url, params={
            "geocode": address,
            "apikey": apikey,
            "format": "json",
        }
        )
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection'][
        'featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lat, lon


def get_distance(location1: tuple, location2: tuple) -> float:
    return distance.distance(location1, location2).km
