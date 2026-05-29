# LLM Compass — Project Context

## What This Is

LLM API 종합 비교 + 예산 가드 오픈소스 프로젝트.
GitHub Pages 기반 웹사이트 + Python CLI 툴(llm-guard).

## 핵심 기능

1. **가격 비교 (자동 갱신)** — 주요 LLM 제공업체 API 가격을 공식 페이지에서 크롤링, 자동 업데이트
2. **예산/용도별 추천** — 사용자의 예산과 목적에 맞는 LLM 조합 추천 (14일 이후 활성화)
3. **AI 종량제 가드** — 토큰 사용량 추적 + 예산 초과 알림 (Telegram)

## 포함할 제공업체

- OpenAI (GPT-4o, GPT-4o-mini, o3, o4-mini)
- Anthropic (Claude Sonnet 4, Haiku 3.5)
- Google (Gemini 2.5 Pro, 2.5 Flash)
- DeepSeek (V3, R1)
- Mistral AI
- Meta Llama 4 (via providers)
- xAI Grok
- MiMo Token Plan (mimo-v2.5, v2.5-pro, v2-flash)
- OpenRouter (라우팅)
- Together AI, Fireworks AI, Groq

## Architecture

```
llm-compass/
├── docs/                    # GitHub Pages (VitePress)
│   ├── pricing/             # 가격표 (자동생성)
│   ├── plans/               # 용도별 추천
│   └── guard/               # 가드 사용법
├── scripts/                 # 자동 갱신
│   ├── fetch-prices.py
│   └── validate.py
├── data/                    # 가격 데이터 JSON
├── llm_guard/               # CLI 툴
│   ├── tracker.py
│   ├── analyzer.py
│   └── alert.py
├── .github/workflows/       # Actions 자동화
└── pyproject.toml
```

## Tech Stack

- Python 3.11+
- VitePress (GitHub Pages)
- GitHub Actions (자동 업데이트)
- pip (llm-guard 배포)

## 라이선스

Apache 2.0 — 기존 tokencost 등과 호환
