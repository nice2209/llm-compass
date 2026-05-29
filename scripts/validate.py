"""prices.json 검증 게이트 — 스키마 + 이상치 탐지.

CI에서 자동 커밋 전에 실행한다. 문제가 있으면 비-0 종료코드로 커밋을 막는다.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import jsonschema  # noqa: E402

DATA_DIR = pathlib.Path("data")


def load_schema(path: str = "data/prices.schema.json") -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def validate_schema(data: dict, schema: dict) -> list[str]:
    """스키마 위반 메시지 목록. 빈 리스트면 통과."""
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]


def detect_anomalies(
    new: dict, previous: dict | None, threshold: float = 0.5
) -> list[str]:
    """전일 대비 입력/출력 단가가 ±threshold(기본 50%)를 초과 변동하면 경고."""
    if not previous:
        return []
    warnings: list[str] = []
    prev_index = _index_by_model(previous)
    for provider, entries in new.get("providers", {}).items():
        for entry in entries:
            key = (provider, entry["model"])
            old = prev_index.get(key)
            if old is None:
                continue
            for field in ("input_per_1m", "output_per_1m"):
                old_val, new_val = old.get(field, 0), entry.get(field, 0)
                if old_val <= 0:
                    continue
                change = abs(new_val - old_val) / old_val
                if change > threshold:
                    warnings.append(
                        f"{provider}/{entry['model']} {field}: "
                        f"{old_val} → {new_val} ({change:.0%} 변동)"
                    )
    return warnings


def _index_by_model(data: dict) -> dict[tuple[str, str], dict]:
    index: dict[tuple[str, str], dict] = {}
    for provider, entries in data.get("providers", {}).items():
        for entry in entries:
            index[(provider, entry["model"])] = entry
    return index


def _load_json(path: pathlib.Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _previous_snapshot(current_date: str) -> dict | None:
    """history에서 현재 날짜를 제외한 가장 최근 스냅샷을 찾는다."""
    history = DATA_DIR / "history"
    if not history.exists():
        return None
    snaps = sorted(
        p for p in history.glob("*.json") if p.stem != current_date
    )
    return _load_json(snaps[-1]) if snaps else None


def main() -> int:
    data = _load_json(DATA_DIR / "prices.json")
    if data is None:
        print("[error] data/prices.json 없음 또는 파싱 실패", file=sys.stderr)
        return 1

    schema = load_schema()
    errors = validate_schema(data, schema)
    if errors:
        print("[error] 스키마 검증 실패:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    previous = _previous_snapshot(data.get("generated_at", "")[:10])
    warnings = detect_anomalies(data, previous)
    for w in warnings:
        print(f"[warn] 이상치: {w}", file=sys.stderr)

    print(f"검증 통과: {len(data.get('providers', {}))} provider")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
