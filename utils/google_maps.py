# services/google_maps.py
from __future__ import annotations

import os
import time
import requests

from dataclasses import dataclass
from typing import Optional


GOOGLE_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


@dataclass(frozen=True)
class GoogleRouteResult:
    distance_m: int
    duration_s: int                 # normal duration
    duration_in_traffic_s: Optional[int]  # traffic duration if available


class GoogleMapsError(Exception):
    pass


def get_distance_and_eta_to_dropoff(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    *,
    departure_time_unix: Optional[int] = None,
    timeout_seconds: int = 6,
) -> GoogleRouteResult:
    """
    Uses Google Distance Matrix API (driving + departure_time) to get traffic-aware ETA.
    duration_in_traffic is returned only when:
    - mode=driving
    - departure_time provided
    - traffic data available
    - valid API key
    """
    api_key = "AIzaSyD-CJUGR3uGQ4dN5BDfj2HfThqIoetaCHE"
    if not api_key:
        raise GoogleMapsError("Missing GOOGLE_MAPS_API_KEY environment variable")

    if departure_time_unix is None:
        departure_time_unix = int(time.time())

    params = {
        "origins": f"{origin_lat},{origin_lng}",
        "destinations": f"{dest_lat},{dest_lng}",
        "mode": "driving",
        "departure_time": departure_time_unix,
        "key": api_key,
    }

    r = requests.get(GOOGLE_DISTANCE_MATRIX_URL, params=params, timeout=timeout_seconds)
    r.raise_for_status()
    payload = r.json()

    if payload.get("status") != "OK":
        raise GoogleMapsError(f"Google API status not OK: {payload.get('status')}")

    rows = payload.get("rows") or []
    if not rows or not rows[0].get("elements"):
        raise GoogleMapsError("Invalid response: missing rows/elements")

    el = rows[0]["elements"][0]
    if el.get("status") != "OK":
        raise GoogleMapsError(f"Element status not OK: {el.get('status')}")

    distance_m = int(el["distance"]["value"])         # meters
    duration_s = int(el["duration"]["value"])         # seconds
    duration_in_traffic = el.get("duration_in_traffic")
    duration_in_traffic_s = int(duration_in_traffic["value"]) if duration_in_traffic else None

    return GoogleRouteResult(
        distance_m=distance_m,
        duration_s=duration_s,
        duration_in_traffic_s=duration_in_traffic_s,
    )