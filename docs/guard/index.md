---
title: llm-guard 사용법
---

# llm-guard — AI 종량제 가드

> 🚧 **준비 중 (Phase 3)** — 아래는 예정된 CLI 인터페이스입니다.

`llm-guard`는 LLM API 토큰 사용량을 기록하고, 동봉된 가격 데이터로 비용을 계산하며, 예산 초과 시 Telegram으로 알림을 보내는 Python CLI 툴입니다.

## 설치 (예정)

```bash
pip install llm-guard
```

## 사용 예시

```bash
# DB 초기화
llm-guard init

# 월 예산 설정 (USD)
llm-guard set-budget 50

# API 호출 기록 — 비용 자동 계산
llm-guard track --provider openai --model gpt-4o --input 1000 --output 500

# 모델별 비용 집계 리포트
llm-guard report
```

## 동작

1. **추적** — 호출의 입력/출력 토큰을 로컬 SQLite(`~/.llm-guard/usage.db`)에 기록
2. **비용 계산** — 동봉된 `prices.json` 기준으로 누적 비용 산출
3. **예산 알림** — 누적 비용이 설정 예산을 넘으면 Telegram Bot으로 알림

## 환경변수 (Telegram 알림용)

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

::: warning 보안
토큰·챗ID 등 비밀값은 반드시 **환경변수**로만 설정하세요. 코드/저장소에 하드코딩하지 마세요.
:::

자세한 진행 상황은 [GitHub 저장소](https://github.com/)를 참고하세요.
