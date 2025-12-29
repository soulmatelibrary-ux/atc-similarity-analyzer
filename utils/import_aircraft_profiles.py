#!/usr/bin/env python3
"""Commercial aircraft profile bulk importer.

Reads data/aircraft_profiles_commercial.csv and upserts into aircraft_profiles table.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "database" / "similarity_detector.db"
DATA_PATH = ROOT_DIR / "data" / "aircraft_profiles_commercial.csv"


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"정수로 변환할 수 없습니다: {value!r}") from None


def load_rows() -> list[Dict[str, Any]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"CSV 데이터가 없습니다: {DATA_PATH}")

    rows: list[Dict[str, Any]] = []
    with DATA_PATH.open(newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for record in reader:
            icao = (record.get("icao_code") or "").strip().upper()
            if not icao:
                continue
            rows.append({
                "icao_code": icao,
                "iata_code": (record.get("iata_code") or "").strip().upper() or None,
                "manufacturer": (record.get("manufacturer") or "").strip() or None,
                "model": (record.get("model") or "").strip() or None,
                "type_description": (record.get("type_description") or "").strip() or None,
                "default_speed_kmh": _to_int(record.get("default_speed_kmh")),
                "default_speed_knots": _to_int(record.get("default_speed_knots")),
                "default_climb_fpm": _to_int(record.get("default_climb_fpm")),
                "default_ceiling_fl": _to_int(record.get("default_ceiling_fl")),
                "notes": (record.get("notes") or "").strip() or None,
            })
    return rows


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"데이터베이스가 없습니다: {DB_PATH}")

    rows = load_rows()
    if not rows:
        print("CSV에 가져올 행이 없습니다.")
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        existing = {row["icao_code"] for row in cursor.execute("SELECT icao_code FROM aircraft_profiles")}
        inserted = updated = 0

        upsert_sql = """
        INSERT INTO aircraft_profiles (
            icao_code, iata_code, manufacturer, model, type_description,
            default_speed_kmh, default_speed_knots, default_climb_fpm,
            default_ceiling_fl, notes, created_at, updated_at
        ) VALUES (
            :icao_code, :iata_code, :manufacturer, :model, :type_description,
            :default_speed_kmh, :default_speed_knots, :default_climb_fpm,
            :default_ceiling_fl, :notes, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT(icao_code) DO UPDATE SET
            iata_code = excluded.iata_code,
            manufacturer = excluded.manufacturer,
            model = excluded.model,
            type_description = excluded.type_description,
            default_speed_kmh = excluded.default_speed_kmh,
            default_speed_knots = excluded.default_speed_knots,
            default_climb_fpm = excluded.default_climb_fpm,
            default_ceiling_fl = excluded.default_ceiling_fl,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
        """

        for row in rows:
            cursor.execute(upsert_sql, row)
            if row["icao_code"] in existing:
                updated += 1
            else:
                inserted += 1

        conn.commit()

    print(f"총 {len(rows)}건 처리 (신규 {inserted}건, 업데이트 {updated}건)")


if __name__ == "__main__":
    main()
