# LLM Compass — 아키텍처 설계

> LLM API 종합 비교 + 예산 가드 시스템
> GitHub Pages(VitePress) 웹사이트 + Python CLI 툴(`llm-guard`)

---

## 1. 시스템 개요

LLM Compass는 세 개의 독립적이지만 데이터로 연결된 서브시스템으로 구성된다.

```
┌─────────────────────────────────────────────────────────────┐
│                       LLM Compass                            │
│                                                              │
│  ┌────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │  크롤러     │───▶│  데이터 저장소 │───▶│  웹사이트(Pages) │  │
│  │ (scripts/) │    │   (data/)     │    │   (docs/)        │  │
│  └────────────┘    └──────────────┘    └─────────────────┘  │
│       ▲                   │                                  │
│       │                   ▼                                  │
│  ┌────────────┐    ┌──────────────┐                          │
│  │  GH Actions │    │  llm-guard   │  (pip 패키지)            │
│  │  (cron)     │    │  (CLI 툴)     │                         │
│  └────────────┘    └──────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

- **크롤러**: 각 제공업체 공식 가격 페이지를 수집해 정규화된 JSON 생성
- **데이터 저장소**: `data/prices.json` (단일 진실 공급원, SSOT)
- **웹사이트**: VitePress가 JSON을 읽어 가격표/추천 페이지 렌더링
- **llm-guard**: 같은 JSON을 패키지에 동봉해 토큰 사용량·비용 추적
- **GitHub Actions**: 매일 크롤러 실행 → JSON 갱신 → 자동 커밋 → Pages 재배포

---

## 2. 디렉토리 구조

```
llm-compass/
├── docs/                       # VitePress 웹사이트 (GitHub Pages)
│   ├── .vitepress/
│   │   ├── config.ts           # 사이트 설정, 사이드바, i18n(ko)
│   │   └── theme/              # 커스텀 테마/컴포넌트
│   │       └── PriceTable.vue  # 가격표 인터랙티브 컴포넌트
│   ├── index.md                # 랜딩 페이지
│   ├── pricing/                # 가격 비교 (데이터 기반 자동 렌더)
│   │   └── index.md
│   ├── plans/                  # 용도별 추천 (Phase 후속, 14일 후 활성)
│   │   └── index.md
│   └── guard/                  # llm-guard 사용법 문서
│       └── index.md
│
├── scripts/                    # 가격 크롤링 / 검증
│   ├── fetch_prices.py         # 메인 오케스트레이터
│   ├── providers/              # 제공업체별 파서 (플러그인)
│   │   ├── base.py             # BaseProvider 추상 클래스
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   ├── google.py
│   │   ├── deepseek.py
│   │   ├── mistral.py
│   │   ├── mimo.py
│   │   ├── openrouter.py
│   │   ├── together.py
│   │   ├── fireworks.py
│   │   └── groq.py
│   ├── validate.py             # 스키마/이상치 검증
│   └── models.py               # 공용 dataclass (PriceEntry 등)
│
├── data/
│   ├── prices.json             # 정규화된 가격 데이터 (SSOT)
│   ├── prices.schema.json      # JSON Schema (검증용)
│   └── history/                # 일자별 스냅샷 (가격 추이용)
│       └── YYYY-MM-DD.json
│
├── llm_guard/                  # CLI 툴 (pip 패키지)
│   ├── __init__.py
│   ├── cli.py                  # argparse/typer 엔트리포인트
│   ├── tracker.py              # 토큰 사용량 기록
│   ├── analyzer.py             # 비용 계산 (prices.json 기반)
│   ├── alert.py                # Telegram 예산 초과 알림
│   ├── store.py                # 로컬 SQLite 저장소
│   └── prices.json             # 패키지 동봉 가격 데이터 (빌드 시 복사)
│
├── tests/
│   ├── test_providers.py
│   ├── test_validate.py
│   └── test_guard.py
│
├── .github/workflows/
│   ├── update-prices.yml       # 일일 크롤링 + 자동 커밋
│   └── deploy-docs.yml         # Pages 배포
│
├── pyproject.toml              # llm-guard 패키지 + scripts 의존성
├── package.json                # VitePress 의존성
├── CLAUDE.md
├── ARCHITECTURE.md
├── SPEC.md
└── LICENSE                     # Apache 2.0
```

---

## 3. 모듈 설명

### 3.1 scripts/ — 크롤링 레이어

| 파일                  | 역할                                                                                                                    |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `fetch_prices.py`     | 모든 provider 파서를 순회 실행, 결과 병합 → `data/prices.json` 작성. 실패한 provider는 기존 데이터 유지(부분 실패 허용) |
| `providers/base.py`   | `BaseProvider` 추상 클래스. `fetch() -> list[PriceEntry]` 인터페이스 강제                                               |
| `providers/<name>.py` | 제공업체별 파서. HTML 스크래핑 또는 공식 API/문서 페이지 파싱                                                           |
| `validate.py`         | 생성된 JSON을 스키마·이상치(전일 대비 ±50% 등) 기준으로 검증                                                            |
| `models.py`           | `PriceEntry`, `ProviderResult` 등 공용 dataclass                                                                        |

**플러그인 패턴**: 새 제공업체 추가 = `providers/`에 파일 하나 + 레지스트리 등록. 코어 수정 불필요.

### 3.2 data/ — 데이터 레이어

- `prices.json`: 모든 소비자(웹/CLI)가 읽는 단일 소스
- `prices.schema.json`: CI와 `validate.py`가 사용하는 계약(contract)
- `history/`: 일자별 스냅샷 → 가격 추이 차트 데이터 소스

### 3.3 docs/ — 프레젠테이션 레이어

- VitePress 빌드 시 `data/prices.json`을 import → `PriceTable.vue`로 렌더링
- 정적 사이트이므로 런타임 API 불필요 (Pages에 적합)
- 한국어 기본, i18n 구조로 영어 확장 여지

### 3.4 llm_guard/ — CLI 레이어

| 파일          | 역할                                                  |
| ------------- | ----------------------------------------------------- |
| `cli.py`      | `llm-guard track / report / set-budget` 등 서브커맨드 |
| `tracker.py`  | API 호출의 입력/출력 토큰을 SQLite에 기록             |
| `analyzer.py` | 동봉된 `prices.json`으로 누적 비용 계산, 모델별 집계  |
| `alert.py`    | 예산 초과 시 Telegram Bot API로 알림                  |
| `store.py`    | SQLite 스키마/CRUD (`~/.llm-guard/usage.db`)          |

---

## 4. 데이터 흐름

### 4.1 가격 갱신 흐름 (일일 자동)

```
GH Actions (cron: daily)
  └─▶ python scripts/fetch_prices.py
        ├─▶ providers/*.fetch()   # 각 공식 페이지 수집
        ├─▶ 정규화 → list[PriceEntry]
        └─▶ data/prices.json 작성 + data/history/YYYY-MM-DD.json 스냅샷
  └─▶ python scripts/validate.py   # 스키마/이상치 검증 (실패 시 abort)
  └─▶ git commit & push            # 변경 있을 때만
  └─▶ deploy-docs.yml 트리거 → VitePress 빌드 → Pages 배포
```

### 4.2 가격 조회 흐름 (사용자)

```
사용자 ──▶ GitHub Pages
            └─▶ PriceTable.vue ──reads──▶ prices.json (빌드 타임 번들)
```

### 4.3 비용 추적 흐름 (CLI)

```
사용자 코드 ──▶ llm-guard track --model gpt-4o --in 1200 --out 800
                  └─▶ tracker.py ──▶ store.py (SQLite 기록)
                  └─▶ analyzer.py ──reads──▶ prices.json (비용 계산)
                  └─▶ 누적 비용 ≥ 예산? ──yes──▶ alert.py ──▶ Telegram
```

---

## 5. API / 데이터 연동 방식

### 5.1 크롤링 전략 (provider별)

| 방식                  | 적용                                                 | 비고                                                |
| --------------------- | ---------------------------------------------------- | --------------------------------------------------- |
| **공식 API/JSON**     | OpenRouter, Together, Fireworks                      | 가격 엔드포인트 제공 → 가장 안정적                  |
| **HTML 스크래핑**     | OpenAI, Anthropic, Google, Mistral                   | 가격 페이지 파싱. 셀렉터 변동 위험 → 검증 단계 필수 |
| **문서/마크다운**     | DeepSeek, Groq                                       | 가격 표가 문서에 정리됨                             |
| **커스텀 엔드포인트** | MiMo Token Plan (`token-plan-sgp.xiaomimimo.com/v1`) | 자체 API 스펙 확인 후 연동                          |

- 각 파서는 **타임아웃·재시도·User-Agent**를 공통 `base.py`에서 제공
- 부분 실패 허용: 한 provider 실패가 전체 갱신을 막지 않음 (기존 값 유지 + 경고 로그)

### 5.2 정규화 계약 (PriceEntry)

모든 파서는 통화 **USD / 1M tokens** 단위로 정규화하여 반환한다.

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "input_per_1m": 2.5,
  "output_per_1m": 10.0,
  "context_window": 128000,
  "currency": "USD",
  "source_url": "https://openai.com/api/pricing/",
  "fetched_at": "2026-05-29T00:00:00Z"
}
```

### 5.3 외부 통신 정책 (보안)

- Telegram 토큰 등 비밀값은 **환경변수**로만 (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)
- 크롤링은 공개 페이지만 대상, 인증 불필요
- `prices.json`에는 비밀값 일절 포함 금지

---

## 6. 기술 스택 / 의존성

| 영역     | 스택                                                                     |
| -------- | ------------------------------------------------------------------------ |
| 크롤러   | Python 3.11+, `httpx`, `selectolax`(또는 `beautifulsoup4`), `jsonschema` |
| 웹       | VitePress 1.x, Vue 3                                                     |
| CLI      | Python 3.11+, `typer`, `rich`, `sqlite3`(표준)                           |
| 자동화   | GitHub Actions                                                           |
| 배포     | GitHub Pages, PyPI (`llm-guard`)                                         |
| 라이선스 | Apache 2.0                                                               |

---

## 7. 설계 원칙

1. **단일 진실 공급원**: `data/prices.json` 하나를 웹/CLI가 공유
2. **플러그인 확장**: provider 추가가 코어를 건드리지 않음
3. **부분 실패 허용**: 한 소스 장애가 시스템 전체를 멈추지 않음
4. **정적 우선**: 런타임 백엔드 없이 Pages만으로 동작 (운영 비용 0)
5. **검증 게이트**: 자동 커밋 전 스키마/이상치 검증 통과 필수
