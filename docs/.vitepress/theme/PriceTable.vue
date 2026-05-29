<script setup lang="ts">
import { computed, ref } from 'vue'
// 빌드 타임에 번들 — 런타임 API 호출 없음
import pricesData from '../../../data/prices.json'

interface PriceEntry {
  provider: string
  model: string
  input_per_1m: number
  output_per_1m: number
  context_window: number
  source_url?: string
  currency?: string
  notes?: string | null
}

interface Row {
  provider: string
  model: string
  inputPer1m: number
  outputPer1m: number
  contextWindow: number
  sourceUrl: string
}

type SortKey = 'inputPer1m' | 'outputPer1m' | 'contextWindow'
type Unit = '1m' | '1k'

const data = pricesData as {
  generated_at?: string
  providers: Record<string, PriceEntry[]>
}

// provider별 뱃지 색상 (깔끔한 솔리드 컬러)
const PROVIDER_COLORS: Record<string, string> = {
  openai: '#10a37f',
  anthropic: '#d4a373',
  google: '#4285f4',
  deepseek: '#4d6bfe',
  mistral: '#fa520f',
  mimo: '#ff6a00',
  openrouter: '#6467f2',
  together: '#0f6fff',
  fireworks: '#5b21b6',
  groq: '#f55036',
}

function providerColor(p: string): string {
  return PROVIDER_COLORS[p] ?? '#64748b'
}

// 유효 행만 추출: 가격 또는 컨텍스트 윈도우 중 하나라도 의미 있는 값이 있어야 함.
// (Phase 1 크롤러가 남긴 잡음 행 — 전부 0 — 은 제외)
const allRows = computed<Row[]>(() => {
  const out: Row[] = []
  for (const [provider, entries] of Object.entries(data.providers ?? {})) {
    for (const e of entries) {
      const input = e.input_per_1m ?? 0
      const output = e.output_per_1m ?? 0
      const ctx = e.context_window ?? 0
      if (input <= 0 && output <= 0 && ctx <= 0) continue
      if (!e.model || !e.model.trim()) continue
      out.push({
        provider,
        model: e.model.trim(),
        inputPer1m: input,
        outputPer1m: output,
        contextWindow: ctx,
        sourceUrl: e.source_url ?? '',
      })
    }
  }
  return out
})

const providers = computed<string[]>(() =>
  [...new Set(allRows.value.map((r) => r.provider))].sort(),
)

// 필터/정렬 상태
const query = ref('')
const selectedProviders = ref<Set<string>>(new Set())
const sortKey = ref<SortKey>('inputPer1m')
const sortAsc = ref(true)
const unit = ref<Unit>('1m')
const filtersOpen = ref(false)

function toggleProvider(p: string) {
  const next = new Set(selectedProviders.value)
  next.has(p) ? next.delete(p) : next.add(p)
  selectedProviders.value = next
}

function isProviderActive(p: string): boolean {
  // 아무것도 선택 안 하면 전체 표시
  return selectedProviders.value.size === 0 || selectedProviders.value.has(p)
}

function selectAllProviders() {
  selectedProviders.value = new Set(providers.value)
}

function clearProviders() {
  selectedProviders.value = new Set()
}

function setSort(key: SortKey) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    // 가격은 저렴한 순(오름차순), 컨텍스트는 큰 순(내림차순)이 직관적
    sortAsc.value = key !== 'contextWindow'
  }
}

const filteredRows = computed<Row[]>(() => {
  const q = query.value.trim().toLowerCase()
  let rows = allRows.value.filter((r) => isProviderActive(r.provider))
  if (q) {
    rows = rows.filter(
      (r) =>
        r.model.toLowerCase().includes(q) ||
        r.provider.toLowerCase().includes(q),
    )
  }
  const dir = sortAsc.value ? 1 : -1
  rows = [...rows].sort((a, b) => (a[sortKey.value] - b[sortKey.value]) * dir)
  return rows
})

// 가격 하이라이트: 입력 단가 기준 최저가 (0 제외)
const cheapestInput = computed<number | null>(() => {
  const vals = filteredRows.value
    .map((r) => r.inputPer1m)
    .filter((v) => v > 0)
  return vals.length ? Math.min(...vals) : null
})

function isCheapest(r: Row): boolean {
  return cheapestInput.value !== null && r.inputPer1m === cheapestInput.value
}

// 가격대별 음영: 입력 단가를 로그 스케일로 정규화해 초록(저렴)→빨강(비쌈) 색조 부여
const inputRange = computed<{ min: number; max: number } | null>(() => {
  const vals = filteredRows.value
    .map((r) => r.inputPer1m)
    .filter((v) => v > 0)
  if (!vals.length) return null
  return { min: Math.min(...vals), max: Math.max(...vals) }
})

function tierHue(r: Row): number | null {
  const range = inputRange.value
  if (!range || r.inputPer1m <= 0) return null
  if (range.max === range.min) return 140
  const lr =
    (Math.log(r.inputPer1m) - Math.log(range.min)) /
    (Math.log(range.max) - Math.log(range.min))
  // 140(초록) → 0(빨강)
  return Math.round(140 - lr * 140)
}

function tierStyle(r: Row): Record<string, string> {
  const h = tierHue(r)
  if (h === null) return {}
  return { '--tier': `hsl(${h} 70% 45%)` }
}

// 단위 변환/포맷 (천 단위 콤마 포함)
function fmtPrice(per1m: number): string {
  if (per1m <= 0) return '—'
  const v = unit.value === '1m' ? per1m : per1m / 1000
  const digits = v >= 1 ? 2 : v >= 0.01 ? 3 : 5
  return `$${v.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`
}

function fmtContext(ctx: number): string {
  if (ctx <= 0) return '—'
  if (ctx >= 1000) return `${(ctx / 1000).toLocaleString('en-US')}K`
  return ctx.toLocaleString('en-US')
}

const unitLabel = computed(() => (unit.value === '1m' ? '1M 토큰' : '1K 토큰'))

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'inputPer1m', label: '입력' },
  { key: 'outputPer1m', label: '출력' },
  { key: 'contextWindow', label: '컨텍스트' },
]

function sortIndicator(key: SortKey): string {
  if (sortKey.value !== key) return ''
  return sortAsc.value ? ' ▲' : ' ▼'
}

// CSV 내보내기
function exportCsv() {
  const header = ['provider', 'model', 'input_per_1m_usd', 'output_per_1m_usd', 'context_window']
  const escape = (s: string) => `"${String(s).replace(/"/g, '""')}"`
  const lines = [header.join(',')]
  for (const r of filteredRows.value) {
    lines.push(
      [
        escape(r.provider),
        escape(r.model),
        r.inputPer1m,
        r.outputPer1m,
        r.contextWindow,
      ].join(','),
    )
  }
  const blob = new Blob(['﻿' + lines.join('\n')], {
    type: 'text/csv;charset=utf-8;',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'llm-compass-prices.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function resetFilters() {
  query.value = ''
  selectedProviders.value = new Set()
  sortKey.value = 'inputPer1m'
  sortAsc.value = true
}
</script>

<template>
  <div class="pt">
    <!-- 컨트롤 바 -->
    <div class="pt-controls">
      <div class="pt-search-wrap">
        <svg class="pt-search-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M21 21l-4.35-4.35M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          />
        </svg>
        <input
          v-model="query"
          class="pt-search"
          type="search"
          placeholder="모델명·제공업체 검색 (예: gpt, claude, gemini)"
          aria-label="모델 검색"
        />
      </div>

      <div class="pt-unit" role="group" aria-label="가격 단위">
        <button :class="{ active: unit === '1m' }" @click="unit = '1m'">
          1M
        </button>
        <button :class="{ active: unit === '1k' }" @click="unit = '1k'">
          1K
        </button>
      </div>

      <button class="pt-btn" @click="exportCsv">CSV</button>
      <button class="pt-btn" @click="resetFilters">초기화</button>

      <!-- 모바일: 필터 토글 -->
      <button
        class="pt-filter-toggle"
        :class="{ open: filtersOpen }"
        :aria-expanded="filtersOpen"
        @click="filtersOpen = !filtersOpen"
      >
        필터
        <span class="pt-caret">▾</span>
      </button>
    </div>

    <!-- 정렬 컨트롤 (카드/표 공통) -->
    <div class="pt-sort" role="group" aria-label="정렬 기준">
      <span class="pt-sort-label">정렬</span>
      <button
        v-for="o in SORT_OPTIONS"
        :key="o.key"
        class="pt-sort-btn"
        :class="{ active: sortKey === o.key }"
        @click="setSort(o.key)"
      >
        {{ o.label }}<span class="pt-sort-ind">{{ sortIndicator(o.key) }}</span>
      </button>
    </div>

    <!-- provider 필터 칩 (모바일에서는 접힘) -->
    <div class="pt-filters" :class="{ open: filtersOpen }">
      <div class="pt-providers">
        <label
          v-for="p in providers"
          :key="p"
          class="pt-chip"
          :class="{ on: selectedProviders.has(p) }"
          :style="{ '--c': providerColor(p) }"
        >
          <input
            type="checkbox"
            :checked="selectedProviders.has(p)"
            @change="toggleProvider(p)"
          />
          <span class="pt-dot" />
          {{ p }}
        </label>
      </div>
      <div class="pt-filter-actions">
        <button class="pt-link-btn" @click="selectAllProviders">전체 선택</button>
        <button class="pt-link-btn" @click="clearProviders">전체 해제</button>
      </div>
    </div>

    <div class="pt-meta">
      <strong>{{ filteredRows.length }}</strong>개 모델 · 단위
      <code>{{ unitLabel }}</code>
    </div>

    <!-- 데스크톱/태블릿: 표 -->
    <div class="pt-table-wrap">
      <table class="pt-table">
        <thead>
          <tr>
            <th>제공업체</th>
            <th>모델</th>
            <th class="num sortable" @click="setSort('inputPer1m')">
              입력 단가<span class="ind">{{ sortIndicator('inputPer1m') }}</span>
            </th>
            <th class="num sortable" @click="setSort('outputPer1m')">
              출력 단가<span class="ind">{{ sortIndicator('outputPer1m') }}</span>
            </th>
            <th class="num col-ctx sortable" @click="setSort('contextWindow')">
              컨텍스트<span class="ind">{{ sortIndicator('contextWindow') }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in filteredRows"
            :key="r.provider + '/' + r.model"
            :class="{ cheap: isCheapest(r) }"
            :style="tierStyle(r)"
          >
            <td>
              <span
                class="pt-badge"
                :style="{ background: providerColor(r.provider) }"
              >
                {{ r.provider }}
              </span>
            </td>
            <td class="model">
              <a
                v-if="r.sourceUrl"
                :href="r.sourceUrl"
                target="_blank"
                rel="noopener"
                :title="`${r.provider} 공식 가격 페이지`"
              >
                {{ r.model }}
                <svg class="pt-ext" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M14 3h7v7M21 3l-9 9M19 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </a>
              <span v-else>{{ r.model }}</span>
            </td>
            <td class="num price">
              <span class="price-val">{{ fmtPrice(r.inputPer1m) }}</span>
              <span v-if="isCheapest(r)" class="pt-tag">최저</span>
            </td>
            <td class="num price">{{ fmtPrice(r.outputPer1m) }}</td>
            <td class="num col-ctx">{{ fmtContext(r.contextWindow) }}</td>
          </tr>
          <tr v-if="filteredRows.length === 0">
            <td colspan="5" class="pt-empty">조건에 맞는 모델이 없습니다.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 모바일: 카드 리스트 -->
    <div class="pt-cards">
      <component
        v-for="r in filteredRows"
        :is="r.sourceUrl ? 'a' : 'div'"
        :key="r.provider + '/' + r.model"
        class="pt-card"
        :class="{ cheap: isCheapest(r) }"
        :style="tierStyle(r)"
        :href="r.sourceUrl || undefined"
        :target="r.sourceUrl ? '_blank' : undefined"
        :rel="r.sourceUrl ? 'noopener' : undefined"
      >
        <div class="pt-card-head">
          <span
            class="pt-badge"
            :style="{ background: providerColor(r.provider) }"
          >
            {{ r.provider }}
          </span>
          <span v-if="isCheapest(r)" class="pt-tag">최저가</span>
        </div>
        <div class="pt-card-model">
          {{ r.model }}
          <svg v-if="r.sourceUrl" class="pt-ext" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M14 3h7v7M21 3l-9 9M19 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </div>
        <div class="pt-card-prices">
          <div class="pt-card-cell">
            <span class="pt-card-k">입력</span>
            <span class="pt-card-v">{{ fmtPrice(r.inputPer1m) }}</span>
          </div>
          <div class="pt-card-cell">
            <span class="pt-card-k">출력</span>
            <span class="pt-card-v">{{ fmtPrice(r.outputPer1m) }}</span>
          </div>
          <div class="pt-card-cell">
            <span class="pt-card-k">컨텍스트</span>
            <span class="pt-card-v">{{ fmtContext(r.contextWindow) }}</span>
          </div>
        </div>
      </component>
      <div v-if="filteredRows.length === 0" class="pt-empty">
        조건에 맞는 모델이 없습니다.
      </div>
    </div>
  </div>
</template>

<style scoped>
.pt {
  margin: 1rem 0 2rem;
  --pt-radius: 12px;
}

/* ── 컨트롤 바 ───────────────────────────── */
.pt-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.7rem;
}

.pt-search-wrap {
  position: relative;
  flex: 1 1 260px;
  min-width: 0;
  display: flex;
  align-items: center;
}
.pt-search-icon {
  position: absolute;
  left: 0.7rem;
  width: 16px;
  height: 16px;
  color: var(--vp-c-text-3);
  pointer-events: none;
}
.pt-search {
  width: 100%;
  padding: 0.55rem 0.75rem 0.55rem 2.1rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: var(--pt-radius);
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-size: 0.9rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.pt-search:focus {
  outline: none;
  border-color: var(--vp-c-brand-1);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--vp-c-brand-1) 18%, transparent);
}

.pt-unit {
  display: inline-flex;
  border: 1px solid var(--vp-c-divider);
  border-radius: var(--pt-radius);
  overflow: hidden;
}
.pt-unit button {
  padding: 0.5rem 0.8rem;
  font-size: 0.84rem;
  font-weight: 600;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-2);
  border: none;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.pt-unit button.active {
  background: var(--vp-c-brand-1);
  color: #fff;
}

.pt-btn {
  padding: 0.5rem 0.85rem;
  font-size: 0.84rem;
  font-weight: 600;
  border: 1px solid var(--vp-c-divider);
  border-radius: var(--pt-radius);
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.pt-btn:hover {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}

.pt-filter-toggle {
  display: none;
  align-items: center;
  gap: 0.3rem;
  padding: 0.5rem 0.85rem;
  font-size: 0.84rem;
  font-weight: 600;
  border: 1px solid var(--vp-c-divider);
  border-radius: var(--pt-radius);
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  cursor: pointer;
}
.pt-caret {
  transition: transform 0.2s;
  font-size: 0.7rem;
}
.pt-filter-toggle.open .pt-caret {
  transform: rotate(180deg);
}

/* ── 정렬 컨트롤 ─────────────────────────── */
.pt-sort {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.7rem;
  flex-wrap: wrap;
}
.pt-sort-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--vp-c-text-3);
  margin-right: 0.15rem;
}
.pt-sort-btn {
  padding: 0.32rem 0.7rem;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-2);
  cursor: pointer;
  transition: all 0.15s;
}
.pt-sort-btn:hover {
  border-color: var(--vp-c-brand-1);
}
.pt-sort-btn.active {
  background: var(--vp-c-brand-soft);
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}
.pt-sort-ind {
  font-size: 0.7rem;
}

/* ── provider 필터 ──────────────────────── */
.pt-filters {
  margin-bottom: 0.7rem;
}
.pt-providers {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.pt-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.7rem;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  cursor: pointer;
  user-select: none;
  color: var(--vp-c-text-2);
  transition: all 0.15s;
}
.pt-chip:hover {
  border-color: var(--c);
}
.pt-chip.on {
  border-color: var(--c);
  background: color-mix(in srgb, var(--c) 14%, transparent);
  color: var(--vp-c-text-1);
}
.pt-chip input {
  display: none;
}
.pt-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--c);
  flex: none;
}
.pt-filter-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.55rem;
}
.pt-link-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--vp-c-brand-1);
  cursor: pointer;
}
.pt-link-btn:hover {
  text-decoration: underline;
}

.pt-meta {
  font-size: 0.8rem;
  color: var(--vp-c-text-2);
  margin-bottom: 0.5rem;
}
.pt-meta strong {
  color: var(--vp-c-text-1);
}
.pt-meta code {
  font-size: 0.76rem;
}

/* ── 공통: 뱃지 / 태그 / 외부링크 아이콘 ──── */
.pt-badge {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 6px;
  color: #fff;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
}
.pt-tag {
  display: inline-flex;
  align-items: center;
  margin-left: 0.4rem;
  padding: 0.1rem 0.45rem;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.02em;
  border-radius: 5px;
  background: linear-gradient(135deg, #16a34a, #22c55e);
  color: #fff;
  box-shadow: 0 1px 3px color-mix(in srgb, #16a34a 50%, transparent);
}
.pt-ext {
  width: 12px;
  height: 12px;
  opacity: 0;
  transition: opacity 0.15s;
  vertical-align: -1px;
}

/* ── 데스크톱/태블릿 표 ──────────────────── */
.pt-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--vp-c-divider);
  border-radius: var(--pt-radius);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.pt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.pt-table th,
.pt-table td {
  padding: 0.6rem 0.85rem;
  text-align: left;
  border-bottom: 1px solid var(--vp-c-divider);
  white-space: nowrap;
}
.pt-table tbody tr:last-child td {
  border-bottom: none;
}
.pt-table thead th {
  position: sticky;
  top: 0;
  background: var(--vp-c-bg-soft);
  font-weight: 700;
  font-size: 0.8rem;
  color: var(--vp-c-text-2);
  z-index: 1;
}
.pt-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.pt-table .price {
  font-weight: 600;
  color: var(--vp-c-text-1);
}
.pt-table th.sortable {
  cursor: pointer;
  user-select: none;
}
.pt-table th.sortable:hover {
  color: var(--vp-c-brand-1);
}
.pt-table .ind {
  color: var(--vp-c-brand-1);
}

/* 가격대별 배경 음영 (좌측 컬러 바 + 옅은 틴트) */
.pt-table tbody tr {
  position: relative;
  transition: background 0.12s;
}
.pt-table tbody tr td:first-child {
  box-shadow: inset 3px 0 0 0 var(--tier, transparent);
}
.pt-table tbody tr[style*='--tier'] {
  background: color-mix(in srgb, var(--tier) 6%, transparent);
}
.pt-table tbody tr:hover {
  background: var(--vp-c-bg-soft) !important;
}
.pt-table tr.cheap td:first-child {
  box-shadow: inset 3px 0 0 0 #22c55e;
}

.pt-table td.model a {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--vp-c-text-1);
  text-decoration: none;
  font-weight: 500;
}
.pt-table td.model a:hover {
  color: var(--vp-c-brand-1);
}
.pt-table td.model a:hover .pt-ext {
  opacity: 0.7;
}

.pt-empty {
  text-align: center;
  color: var(--vp-c-text-2);
  padding: 1.6rem;
}

/* ── 모바일 카드 ─────────────────────────── */
.pt-cards {
  display: none;
  flex-direction: column;
  gap: 0.6rem;
}
.pt-card {
  display: block;
  padding: 0.85rem 0.95rem;
  border: 1px solid var(--vp-c-divider);
  border-left: 4px solid var(--tier, var(--vp-c-divider));
  border-radius: var(--pt-radius);
  background: var(--vp-c-bg);
  text-decoration: none;
  color: inherit;
  transition: transform 0.12s, box-shadow 0.12s;
}
.pt-card[href]:active {
  transform: scale(0.99);
}
.pt-card[href] {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.pt-card[style*='--tier'] {
  background: color-mix(in srgb, var(--tier) 5%, var(--vp-c-bg));
}
.pt-card.cheap {
  border-left-color: #22c55e;
}
.pt-card-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}
.pt-card-model {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.98rem;
  font-weight: 700;
  color: var(--vp-c-text-1);
  margin-bottom: 0.7rem;
  word-break: break-word;
}
.pt-card[href] .pt-ext {
  opacity: 0.5;
}
.pt-card-prices {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}
.pt-card-cell {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  padding: 0.45rem 0.5rem;
  background: var(--vp-c-bg-soft);
  border-radius: 8px;
  text-align: center;
}
.pt-card-k {
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--vp-c-text-3);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.pt-card-v {
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--vp-c-text-1);
  font-variant-numeric: tabular-nums;
}

/* ── 반응형 분기 ─────────────────────────── */
/* 태블릿 (640–1024px): 컨텍스트 컬럼 숨김 */
@media (min-width: 640px) and (max-width: 1024px) {
  .col-ctx {
    display: none;
  }
}

/* 모바일 (<640px): 카드 전환 + 필터 접기 */
@media (max-width: 639px) {
  .pt-table-wrap {
    display: none;
  }
  .pt-cards {
    display: flex;
  }
  .pt-controls {
    gap: 0.4rem;
  }
  .pt-search-wrap {
    flex-basis: 100%;
  }
  .pt-filter-toggle {
    display: inline-flex;
  }
  .pt-filters {
    display: none;
    padding: 0.6rem;
    border: 1px solid var(--vp-c-divider);
    border-radius: var(--pt-radius);
    background: var(--vp-c-bg-soft);
  }
  .pt-filters.open {
    display: block;
  }
}
</style>
