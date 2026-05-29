"""가격 크롤링 오케스트레이터.

모든 provider를 순회 실행하고 결과를 병합해 data/prices.json을 생성한다.
provider별 try/except로 격리 — 한 곳이 실패해도 나머지는 갱신되고,
실패한 provider는 이전(previous) 값을 유지한다(부분 실패 허용).
"""

from __future__ import annotations

import json
import pathlib
import sys

# `python scripts/fetch_prices.py` 직접 실행 시 리포 루트를 import 경로에 추가
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from scripts.models import ProviderResult  # noqa: E402
from scripts.providers import get_all_providers  # noqa: E402
from scripts.providers.base import BaseProvider, now_iso  # noqa: E402

SCHEMA_VERSION = 1


def run_provider(cls: type[BaseProvider], client: httpx.Client) -> ProviderResult:
    """단일 provider를 격리 실행. 예외는 ProviderResult.error로 캡처한다."""
    try:
        entries = cls(client).fetch()
        return ProviderResult(provider=cls.name, entries=entries, ok=True)
    except Exception as exc:  # noqa: BLE001 — 부분 실패 허용
        print(f"[warn] provider '{cls.name}' 실패: {exc}", file=sys.stderr)
        return ProviderResult(
            provider=cls.name, entries=[], ok=False, error=str(exc)
        )


def merge_results(
    results: list[ProviderResult], previous: dict | None
) -> dict:
    """성공분은 새 값으로 갱신, 실패분은 previous 값을 유지한다."""
    prev_providers = (previous or {}).get("providers", {})
    providers: dict[str, list[dict]] = {}
    for r in results:
        if r.ok:
            providers[r.provider] = [e.to_dict() for e in r.entries]
        else:
            providers[r.provider] = prev_providers.get(r.provider, [])
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "providers": providers,
    }


def write_outputs(data: dict, out_dir: str = "data") -> None:
    """prices.json과 history/<date>.json 스냅샷을 작성한다."""
    base = pathlib.Path(out_dir)
    base.mkdir(parents=True, exist_ok=True)
    (base / "prices.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    history = base / "history"
    history.mkdir(exist_ok=True)
    date = data["generated_at"][:10]  # YYYY-MM-DD
    (history / f"{date}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _load_previous(out_dir: str = "data") -> dict | None:
    path = pathlib.Path(out_dir) / "prices.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def main() -> int:
    previous = _load_previous()
    with httpx.Client(follow_redirects=True) as client:
        results = [run_provider(cls, client) for cls in get_all_providers()]
    data = merge_results(results, previous)
    write_outputs(data)

    ok = sum(1 for r in results if r.ok)
    total_models = sum(len(v) for v in data["providers"].values())
    print(
        f"완료: {ok}/{len(results)} provider 성공, "
        f"{len(data['providers'])} provider 키, 총 {total_models} 모델"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
