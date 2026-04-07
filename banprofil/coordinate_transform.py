from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SwerefPoint:
    e: float
    n: float


def wgs84_to_sweref99tm(latitude: float, longitude: float) -> SwerefPoint:
    """Convert WGS84 latitude/longitude (EPSG:4326) to SWEREF 99 TM (EPSG:3006)."""
    axis = 6378137.0
    flattening = 1.0 / 298.257222101
    central_meridian = math.radians(15.0)
    scale = 0.9996
    false_northing = 0.0
    false_easting = 500000.0

    e2 = flattening * (2.0 - flattening)
    n = flattening / (2.0 - flattening)
    a_roof = axis / (1.0 + n) * (1.0 + n * n / 4.0 + n**4 / 64.0)

    a = e2
    b = (5.0 * e2**2 - e2**3) / 6.0
    c = (104.0 * e2**3 - 45.0 * e2**4) / 120.0
    d = (1237.0 * e2**4) / 1260.0

    beta1 = n / 2.0 - 2.0 * n**2 / 3.0 + 5.0 * n**3 / 16.0 + 41.0 * n**4 / 180.0
    beta2 = 13.0 * n**2 / 48.0 - 3.0 * n**3 / 5.0 + 557.0 * n**4 / 1440.0
    beta3 = 61.0 * n**3 / 240.0 - 103.0 * n**4 / 140.0
    beta4 = 49561.0 * n**4 / 161280.0

    lat = math.radians(latitude)
    lon = math.radians(longitude)
    lon_diff = lon - central_meridian

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)

    lat_star = lat - sin_lat * cos_lat * (
        a + b * sin_lat**2 + c * sin_lat**4 + d * sin_lat**6
    )
    xi_prim = math.atan(math.tan(lat_star) / math.cos(lon_diff))
    eta_prim = math.atanh(math.cos(lat_star) * math.sin(lon_diff))

    northing = scale * a_roof * (
        xi_prim
        + beta1 * math.sin(2.0 * xi_prim) * math.cosh(2.0 * eta_prim)
        + beta2 * math.sin(4.0 * xi_prim) * math.cosh(4.0 * eta_prim)
        + beta3 * math.sin(6.0 * xi_prim) * math.cosh(6.0 * eta_prim)
        + beta4 * math.sin(8.0 * xi_prim) * math.cosh(8.0 * eta_prim)
    ) + false_northing

    easting = scale * a_roof * (
        eta_prim
        + beta1 * math.cos(2.0 * xi_prim) * math.sinh(2.0 * eta_prim)
        + beta2 * math.cos(4.0 * xi_prim) * math.sinh(4.0 * eta_prim)
        + beta3 * math.cos(6.0 * xi_prim) * math.sinh(6.0 * eta_prim)
        + beta4 * math.cos(8.0 * xi_prim) * math.sinh(8.0 * eta_prim)
    ) + false_easting

    return SwerefPoint(e=round(easting, 3), n=round(northing, 3))
