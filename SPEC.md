# LLM Compass — 개발 스펙

> 6일(3 Phase) 개발 계획. 각 Phase는 파일 목록 · 함수 시그니처 · 데이터 구조를 포함한다.
> Python 3.11+, 타입힌트 필수.

---

## 공용 데이터 구조

전 Phase가 공유하는 핵심 모델 (`scripts/models.py`).

```python
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class PriceEntry:
    provider: str            # "openai"
    model: str               # "gpt-4o"
    input_per_1m: float      # USD / 1M input tokens
    output_per_1m: float     # USD / 1M output tokens
    context_window: int      # 128000
    source_url: str
    fetched_at: str          # ISO8601 UTC
    currency: str = "USD"
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ProviderResult:
    provider: str
    entries: list[PriceEntry]
    ok: bool
    error: Optional[str] = None
```

`data/prices.json` 최종 형태:

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-29T00:00:00Z",
  "providers": {
    "openai": [ { /* PriceEntry */ } ],
    "anthropic": [ ... ]
  }
}
```

---

## Phase 1 (Day 1–2) — 가격 크롤링 스크립트

### 목표

10개 제공업체 가격을 수집해 검증된 `data/prices.json`을 생성한다.

### 파일 목록

```
scripts/
├── models.py            # PriceEntry, ProviderResult
├── fetch_prices.py      # 오케스트레이터 + 레지스트리
├── validate.py          # 스키마/이상치 검증
└── providers/
    ├── __init__.py      # PROVIDERS 레지스트리
    ├── base.py          # BaseProvider
    ├── openai.py  anthropic.py  google.py  deepseek.py
    ├── mistral.py  mimo.py  openrouter.py
    └── together.py  fireworks.py  groq.py
data/
├── prices.schema.json
└── (생성) prices.json, history/YYYY-MM-DD.json
```

### 함수 시그니처

```python
# providers/base.py
class BaseProvider(ABC):
    name: str
    source_url: str

    def __init__(self, client: httpx.Client) -> None: ...

    @abstractmethod
    def fetch(self) -> list[PriceEntry]:
        """공식 페이지를 파싱해 정규화된 가격 목록 반환. 실패 시 예외."""

    def _get(self, url: str, **kw) -> httpx.Response:
        """타임아웃·재시도·UA 포함 공통 GET."""

# providers/__init__.py
PROVIDERS: dict[str, type[BaseProvider]]   # name -> class
def get_all_providers() -> list[type[BaseProvider]]: ...

# providers/openai.py (각 provider 동일 패턴)
class OpenAIProvider(BaseProvider):
    name = "openai"
    source_url = "https://openai.com/api/pricing/"
    def fetch(self) -> list[PriceEntry]: ...

# fetch_prices.py
def run_provider(cls: type[BaseProvider], client) -> ProviderResult: ...
def merge_results(results: list[ProviderResult],
                  previous: dict | None) -> dict:
    """성공분은 갱신, 실패분은 previous 유지."""
def write_outputs(data: dict, out_dir: str = "data") -> None:
    """prices.json + history/<date>.json 작성."""
def main() -> int: ...

# validate.py
def load_schema(path: str = "data/prices.schema.json") -> dict: ...
def validate_schema(data: dict, schema: dict) -> list[str]: ...
def detect_anomalies(new: dict, previous: dict | None,
                     threshold: float = 0.5) -> list[str]:
    """전일 대비 ±threshold 초과 변동 탐지."""
def main() -> int:   # 0=pass, 1=fail (CI 게이트)
```

### 동작 규약

- `fetch_prices.py`는 provider별 try/except로 격리 → 부분 실패 허용
- 모든 가격은 **USD / 1M tokens** 정규화
- `validate.py`는 비정상 시 비-0 종료코드 → Actions에서 커밋 차단

### 검증 (verify)

- `python scripts/fetch_prices.py` → `data/prices.json` 생성, 10개 provider 키 존재
- `python scripts/validate.py` → exit 0
- `pytest tests/test_providers.py` → 각 파서가 고정 HTML fixture에서 PriceEntry 반환

---

## Phase 2 (Day 3–4) — GitHub Pages 사이트

### 목표

`prices.json`을 읽어 정렬·필터 가능한 가격 비교표를 정적 사이트로 배포한다.

### 파일 목록

```
docs/
├── .vitepress/
│   ├── config.ts             # 사이트/사이드바/한국어 설정
│   └── theme/
│       ├── index.ts          # 테마 등록
│       └── PriceTable.vue     # 인터랙티브 가격표
├── index.md                  # 랜딩
├── pricing/index.md          # 가격 비교 (PriceTable 임베드)
├── plans/index.md            # 용도별 추천 (placeholder, 14일 후 활성)
└── guard/index.md            # llm-guard 사용법
package.json
.github/workflows/deploy-docs.yml
```

### 핵심 컴포넌트 / 시그니처

```typescript
// .vitepress/config.ts
export default defineConfig({
  lang: 'ko-KR',
  title: 'LLM Compass',
  base: '/llm-compass/',
  themeConfig: { nav: [...], sidebar: {...} }
})
```

```vue
<!-- PriceTable.vue -->
<script setup lang="ts">
import prices from '../../../data/prices.json'
interface Row {
  provider: string; model: string
  inputPer1m: number; outputPer1m: number; contextWindow: number
}
// flatten providers -> Row[]
const sortKey = ref<'inputPer1m' | 'outputPer1m'>('inputPer1m')
const query = ref('')
const rows = computed<Row[]>(() => /* filter + sort */)
</script>
```

기능: provider/모델 검색, 입력/출력 단가 정렬, 컨텍스트 윈도우 표시, 1M·1K 단위 토글.

### deploy-docs.yml (요지)

```yaml
on:
  push: { branches: [main], paths: ["docs/**", "data/**"] }
  workflow_dispatch:
jobs:
  deploy: # npm ci → vitepress build → actions/deploy-pages
```

### 검증 (verify)

- `npm run docs:build` → 빌드 성공, 에러 0
- 로컬 `npm run docs:dev` → /pricing 에서 표 렌더, 정렬·검색 동작
- Pages 배포 후 URL 접속 확인

---

## Phase 3 (Day 5–6) — llm-guard CLI 툴

### 목표

토큰 사용량을 기록하고 `prices.json`으로 비용을 계산, 예산 초과 시 Telegram 알림.

### 파일 목록

```
llm_guard/
├── __init__.py        # __version__
├── cli.py             # typer 엔트리포인트
├── tracker.py
├── analyzer.py
├── alert.py
├── store.py
└── prices.json        # 빌드 시 data/ 에서 복사
tests/test_guard.py
pyproject.toml          # [project.scripts] llm-guard = "llm_guard.cli:app"
```

### 데이터 구조 (SQLite, `~/.llm-guard/usage.db`)

```sql
CREATE TABLE usage (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,           -- ISO8601
  provider TEXT, model TEXT,
  input_tokens INTEGER, output_tokens INTEGER,
  cost_usd REAL
);
CREATE TABLE budget (
  period TEXT PRIMARY KEY,    -- 'monthly'
  limit_usd REAL NOT NULL
);
```

### 함수 시그니처

```python
# store.py
def get_db() -> sqlite3.Connection: ...
def init_db() -> None: ...
def insert_usage(rec: dict) -> None: ...
def sum_cost(period: str = "monthly") -> float: ...
def set_budget(period: str, limit_usd: float) -> None: ...
def get_budget(period: str = "monthly") -> float | None: ...

# analyzer.py
def load_prices() -> dict: ...                       # 동봉 prices.json
def cost_of(provider: str, model: str,
            input_tokens: int, output_tokens: int) -> float: ...
def report(period: str = "monthly") -> dict:         # 모델별 집계

# tracker.py
def track(provider: str, model: str,
          input_tokens: int, output_tokens: int) -> float:
    """비용 계산 → 기록 → 예산 체크. 반환: 이번 호출 비용."""

# alert.py
def send_telegram(message: str) -> bool: ...         # env 토큰 사용
def check_and_alert(current: float, limit: float) -> None: ...

# cli.py  (typer)
@app.command() def track(provider, model, input, output): ...
@app.command() def report(period: str = "monthly"): ...
@app.command() def set_budget(limit: float, period: str = "monthly"): ...
@app.command() def init(): ...
```

### 동작 규약

- Telegram 토큰/챗ID는 환경변수만 (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)
- 예산 미설정 시 알림 생략, 추적은 계속
- 가격에 없는 모델은 경고 + cost 0 기록 (추적 중단 안 함)

### 검증 (verify)

- `pip install -e .` → `llm-guard --help` 동작
- `llm-guard track --provider openai --model gpt-4o --input 1000 --output 500` → 비용 출력 + DB 기록
- `llm-guard report` → 모델별 집계 표 (rich)
- `pytest tests/test_guard.py` → cost_of/track/예산 경계 케이스 통과

---

## 마일스톤 요약

| Phase | Day | 산출물               | 완료 기준                         |
| ----- | --- | -------------------- | --------------------------------- |
| 1     | 1–2 | 크롤러 + prices.json | validate.py exit 0, 10 provider   |
| 2     | 3–4 | VitePress 사이트     | Pages 배포, 가격표 동작           |
| 3     | 5–6 | llm-guard CLI        | pip 설치, track/report/alert 동작 |
