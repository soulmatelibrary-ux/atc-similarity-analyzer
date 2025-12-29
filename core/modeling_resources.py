"""Shared loaders for route/sector reference data used by trajectory calculations."""
import os
from functools import lru_cache
from pathlib import Path

from core import route_converter
from core.flight_processor import load_sectors

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _build_coord_map(enroute_df, fix_col):
    coord_map = {}
    for _, row in enroute_df.iterrows():
        fix = str(row.get(fix_col, "") or "").strip().upper()
        if not fix or fix == "NAN":
            continue
        try:
            lat = float(row["LAT"])
            lon = float(row["LON"])
        except (TypeError, ValueError):
            continue
        if fix not in coord_map:
            coord_map[fix] = (lat, lon)
    return coord_map


@lru_cache(maxsize=1)
def get_modeling_resources():
    """Load and cache reference datasets for waypoint and sector calculations."""
    enroute_path = PROJECT_ROOT / "data" / "enroute" / "enroute.xlsx"
    sector_path = PROJECT_ROOT / "data" / "sectors" / "sector1.xlsx"

    if not enroute_path.exists():
        raise FileNotFoundError(f"enroute.xlsx 파일을 찾을 수 없습니다: {enroute_path}")
    if not sector_path.exists():
        raise FileNotFoundError(f"sector1.xlsx 파일을 찾을 수 없습니다: {sector_path}")

    enroute_df, fix_col = route_converter.load_data(str(enroute_path))
    coord_map = _build_coord_map(enroute_df, fix_col)
    if not coord_map:
        raise ValueError("경유 지점 좌표 데이터를 불러오지 못했습니다.")

    sectors = load_sectors(str(sector_path))
    if not sectors:
        raise ValueError("섹터 데이터가 비어 있습니다. sector1.xlsx을 확인하세요.")

    return {
        "enroute_df": enroute_df,
        "fix_col": fix_col,
        "coord_map": coord_map,
        "sectors": sectors,
    }
