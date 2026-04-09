from __future__ import annotations

from shapely import wkb

from .gpkg_inspector import GeoPackageInspector, GeoPackageInspectorError


class GeoPackageGeometryError(Exception):
    """Basundantag för GeoPackage-geometritolkning."""


def load_geometry(geom: bytes):
    """
    Läser Shapely-geometri från GeoPackageBinary.

    Parameters
    ----------
    geom : bytes
        GeoPackageBinary-geometri.

    Returns
    -------
    shapely.geometry.base.BaseGeometry
        Tolkat geometriobjekt.
    """
    try:
        header = GeoPackageInspector.inspect_geometry_header_static(geom)
    except GeoPackageInspectorError as exc:
        raise GeoPackageGeometryError(str(exc)) from exc
    try:
        return wkb.loads(geom[header.wkb_offset:])
    except Exception as exc:
        raise GeoPackageGeometryError(f"Could not parse WKB at offset {header.wkb_offset}") from exc


def point_xy(geom: bytes | None) -> tuple[float, float] | None:
    """
    Hämtar X/Y från punktgeometri.

    Parameters
    ----------
    geom : bytes | None
        GeoPackageBinary-punkt.

    Returns
    -------
    tuple[float, float] | None
        X och Y, eller `None` om tolkning misslyckas.
    """
    if not isinstance(geom, bytes):
        return None
    geometry = load_geometry(geom)
    coords = list(geometry.coords)
    if not coords:
        return None
    return float(coords[0][0]), float(coords[0][1])


def line_vertices_xyzm(geom: bytes | None) -> list[tuple[float, ...]]:
    """
    Hämtar koordinater från linjegeometri.

    Parameters
    ----------
    geom : bytes | None
        GeoPackageBinary-linje.

    Returns
    -------
    list[tuple[float, ...]]
        Kompletta koordinattupler enligt geometriinnehållet.
    """
    if not isinstance(geom, bytes):
        return []
    geometry = load_geometry(geom)
    return [tuple(float(value) for value in coord) for coord in geometry.coords]


def line_vertices_xy(geom: bytes | None) -> list[tuple[float, float]]:
    """
    Hämtar X/Y-vertexlista från linjegeometri.

    Parameters
    ----------
    geom : bytes | None
        GeoPackageBinary-linje.

    Returns
    -------
    list[tuple[float, float]]
        Vertexlista i XY.
    """
    return [(coord[0], coord[1]) for coord in line_vertices_xyzm(geom)]
