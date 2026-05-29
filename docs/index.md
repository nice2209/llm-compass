---
layout: home

hero:
  name: LLM Compass
  text: LLM API 가격 비교 + 예산 가드
  tagline: 주요 LLM 제공업체의 API 가격을 한눈에 비교하고, 예산을 초과하기 전에 알림을 받으세요.
  actions:
    - theme: brand
      text: 가격 비교 보기
      link: /pricing/
    - theme: alt
      text: llm-guard 사용법
      link: /guard/
    - theme: alt
      text: GitHub
      link: https://github.com/

features:
  - icon: 📊
    title: 가격 비교 (자동 갱신)
    details: OpenAI, Anthropic, Google, DeepSeek, Mistral, xAI 등 주요 제공업체의 API 가격을 공식 페이지에서 매일 수집해 정렬·필터 가능한 표로 제공합니다.
  - icon: 🎯
    title: 용도별 추천
    details: 예산과 목적(코딩, 요약, 대량 처리 등)에 맞는 최적의 LLM 조합을 추천합니다. (14일 이후 활성화)
  - icon: 🛡️
    title: AI 종량제 가드
    details: llm-guard CLI로 토큰 사용량을 추적하고, 예산 초과 시 Telegram으로 즉시 알림을 받습니다.
---

## LLM Compass란?

**LLM Compass**는 난립하는 LLM API 가격을 투명하게 비교하고, 비용을 통제할 수 있게 돕는 오픈소스 프로젝트입니다. GitHub Pages 기반 웹사이트와 Python CLI 툴(`llm-guard`)로 구성됩니다.

모든 가격 데이터는 단일 JSON(`data/prices.json`)을 진실 공급원(SSOT)으로 삼아 웹과 CLI가 공유합니다.

## 개발 단계

| Phase       | 내용                                                           | 산출물             |
| ----------- | -------------------------------------------------------------- | ------------------ |
| **Phase 1** | 가격 크롤링 — 10개 제공업체 공식 페이지에서 가격을 수집·정규화 | `data/prices.json` |
| **Phase 2** | GitHub Pages 사이트 — 정렬·필터 가능한 가격 비교표 배포        | 이 웹사이트        |
| **Phase 3** | llm-guard CLI — 토큰 사용량 추적 + 예산 초과 Telegram 알림     | pip 패키지         |

## 포함 제공업체

OpenAI · Anthropic · Google · DeepSeek · Mistral AI · Meta Llama · xAI Grok · MiMo · OpenRouter · Together AI · Fireworks AI · Groq

## 라이선스

Apache 2.0 — `tokencost` 등 기존 도구와 호환됩니다.
