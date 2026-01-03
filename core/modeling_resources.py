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
            # DB 컬럼명은 소문자 (lat, lon)
            lat = float(row.get("lat") or row.get("LAT"))
            lon = float(row.get("lon") or row.get("LON"))
        except (TypeError, ValueError, KeyError):
            continue
        if fix not in coord_map:
            coord_map[fix] = (lat, lon)
    return coord_map


@lru_cache(maxsize=1)
def get_modeling_resources():
    """Load and cache reference datasets for waypoint and sector calculations."""
    from database.db_manager import DatabaseManager

    db_manager = DatabaseManager()

    # DB에서 경유지점 데이터 로드
    enroute_df = db_manager.get_all_waypoints_df()
    if enroute_df.empty:
        raise RuntimeError("waypoints 테이블이 비어있습니다. 데이터베이스를 확인하세요.")

    fix_col = 'fixpnt'  # DB 컬럼명
    coord_map = _build_coord_map(enroute_df, fix_col)
    if not coord_map:
        raise ValueError("경유 지점 좌표 데이터를 불러오지 못했습니다.")

    # DB에서 섹터 경계 데이터 로드
    sectors = db_manager.get_sector_boundaries_dict()
    if not sectors:
        raise RuntimeError("sector_boundaries 테이블이 비어있습니다. 데이터베이스를 확인하세요.")

    return {
        "enroute_df": enroute_df,
        "fix_col": fix_col,
        "coord_map": coord_map,
        "sectors": sectors,
    }
