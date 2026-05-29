# Phase 1 실행 프롬프트 — 가격 크롤링 스크립트

> 아래 블록을 Claude Code에 그대로 붙여넣으면 Phase 1을 바로 구현한다.
> 사전에 `ARCHITECTURE.md`, `SPEC.md`가 리포 루트에 있다고 가정한다.

---

## 복사용 프롬프트

```
LLM Compass 프로젝트의 Phase 1(가격 크롤링 스크립트)을 구현해줘.
ARCHITECTURE.md와 SPEC.md를 먼저 읽고 그 설계를 따른다.

## 목표
10개 LLM 제공업체의 API 가격을 공식 페이지에서 수집해
검증된 data/prices.json을 생성하는 크롤링 시스템을 만든다.

## 대상 제공업체 (source_url)
- openai      : https://openai.com/api/pricing/
- anthropic   : https://www.anthropic.com/pricing#anthropic-api
- google      : https://ai.google.dev/gemini-api/docs/pricing
- deepseek    : https://api-docs.deepseek.com/quick_start/pricing
- mistral     : https://mistral.ai/pricing#api-pricing
- mimo        : https://token-plan-sgp.xiaomimimo.com/v1   (자체 API, 스펙 확인 후 연동)
- openrouter  : https://openrouter.ai/api/v1/models        (JSON API)
- together    : https://api.together.xyz/v1/models         (JSON API)
- fireworks   : https://fireworks.ai/pricing
- groq        : https://groq.com/pricing/

## 생성할 파일
scripts/models.py
scripts/fetch_prices.py
scripts/validate.py
scripts/providers/__init__.py
scripts/providers/base.py
scripts/providers/{openai,anthropic,google,deepseek,mistral,mimo,openrouter,together,fireworks,groq}.py
data/prices.schema.json
tests/test_providers.py
tests/fixtures/   (각 provider HTML/JSON 샘플)
pyproject.toml   (scripts 의존성: httpx, selectolax, jsonschema, pytest)

## 데이터 구조 (scripts/models.py)
@dataclass PriceEntry:
  provider, model: str
  input_per_1m, output_per_1m: float   # USD / 1M tokens 로 정규화
  context_window: int
  source_url, fetched_at: str          # fetched_at = ISO8601 UTC
  currency: str = "USD"
  notes: Optional[str] = None
@dataclass ProviderResult:
  provider: str; entries: list[PriceEntry]; ok: bool; error: Optional[str]

data/prices.json 형태:
{ "schema_version": 1, "generated_at": <ISO>,
  "providers": { "openai": [PriceEntry...], ... } }

## 클래스/함수 (SPEC.md와 동일하게)
providers/base.py:
  class BaseProvider(ABC):
    name: str; source_url: str
    def __init__(self, client: httpx.Client)
    @abstractmethod def fetch(self) -> list[PriceEntry]
    def _get(self, url, **kw) -> httpx.Response   # 타임아웃 15s, 재시도 2회, UA 설정

providers/__init__.py:
  PROVIDERS: dict[str, type[BaseProvider]]   # 모든 provider 등록
  def get_all_providers() -> list[type[BaseProvider]]

각 providers/<name>.py:
  class <Name>Provider(BaseProvider):
    name = "..."; source_url = "..."
    def fetch(self) -> list[PriceEntry]

fetch_prices.py:
  def run_provider(cls, client) -> ProviderResult   # try/except 격리
  def merge_results(results, previous) -> dict        # 실패분은 previous 유지
  def write_outputs(data, out_dir="data")            # prices.json + history/<date>.json
  def main() -> int

validate.py:
  def load_schema(path="data/prices.schema.json") -> dict
  def validate_schema(data, schema) -> list[str]
  def detect_anomalies(new, previous, threshold=0.5) -> list[str]
  def main() -> int   # 0=pass, 1=fail

## 구현 규칙
- Python 3.11+, 전 함수 타입힌트 필수
- 모든 가격은 USD / 1M tokens 로 정규화 (페이지가 1K 단위면 ×1000)
- provider별 try/except로 격리 → 한 곳 실패가 전체를 막지 않음 (부분 실패 허용)
- 실패한 provider는 previous prices.json 값 유지 + stderr 경고 로그
- HTML 스크래핑은 selectolax 사용, JSON API는 httpx 직접 파싱
- 비밀값/토큰 하드코딩 금지 (Phase 1엔 인증 불필요, 공개 페이지만)
- HTML 셀렉터는 변동 가능 → 파서별 함수로 분리하고 fixture 테스트 작성

## 테스트 (TDD 우선)
- tests/fixtures/ 에 각 provider 응답 샘플 저장
- tests/test_providers.py: 각 파서가 fixture에서 올바른 PriceEntry 리스트를 반환하는지 검증
- 네트워크 호출 없이 fixture 기반으로 동작하도록 _get을 monkeypatch

## 완료 기준 (반드시 검증 후 보고)
1. python scripts/fetch_prices.py  →  data/prices.json 생성, providers 키 10개 존재
2. python scripts/validate.py      →  exit 0
3. pytest tests/test_providers.py  →  전체 통과
4. 변경 파일 목록 요약

먼저 models.py와 base.py로 골격을 잡고, openai 파서 + 테스트를 TDD로 완성한 뒤
나머지 provider로 같은 패턴을 확장해. provider 파서는 병렬로 작업 가능.
```

---

## 설치 / 실행 방법

```bash
# 1. 의존성 설치 (uv 권장)
uv venv && source .venv/bin/activate
uv pip install httpx selectolax jsonschema pytest
# 또는: pip install httpx selectolax jsonschema pytest

# 2. 크롤링 실행
python scripts/fetch_prices.py
#  → data/prices.json, data/history/YYYY-MM-DD.json 생성

# 3. 검증
python scripts/validate.py
#  → exit 0 이면 통과

# 4. 테스트
pytest tests/test_providers.py -v
```

### GitHub Actions 연동 (Phase 1 완료 후)

```yaml
# .github/workflows/update-prices.yml
name: Update Prices
on:
  schedule: [{ cron: "0 0 * * *" }] # 매일 00:00 UTC
  workflow_dispatch:
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install httpx selectolax jsonschema
      - run: python scripts/fetch_prices.py
      - run: python scripts/validate.py
      - name: Commit if changed
        run: |
          git config user.name  "llm-compass-bot"
          git config user.email "bot@users.noreply.github.com"
          git add data/
          git diff --cached --quiet || git commit -m "chore: 가격 데이터 자동 갱신"
          git push
```
