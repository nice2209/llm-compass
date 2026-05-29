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

// provider별 뱃지 색상 (배경, 글자)
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

function toggleProvider(p: string) {
  const next = new Set(selectedProviders.value)
  next.has(p) ? next.delete(p) : next.add(p)
  selectedProviders.value = next
}

function isProviderActive(p: string): boolean {
  // 아무것도 선택 안 하면 전체 표시
  return selectedProviders.value.size === 0 || selectedProviders.value.has(p)
}

function setSort(key: SortKey) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    sortAsc.value = true
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

// 단위 변환/포맷
function fmtPrice(per1m: number): string {
  if (per1m <= 0) return '—'
  const v = unit.value === '1m' ? per1m : per1m / 1000
  // 소수점은 값 크기에 따라 가변
  const digits = v >= 1 ? 2 : v >= 0.01 ? 3 : 5
  return `$${v.toFixed(digits)}`
}

function fmtContext(ctx: number): string {
  if (ctx <= 0) return '—'
  if (ctx >= 1000) return `${(ctx / 1000).toLocaleString('ko-KR')}K`
  return ctx.toLocaleString('ko-KR')
}

const unitLabel = computed(() => (unit.value === '1m' ? '1M 토큰' : '1K 토큰'))

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
      <input
        v-model="query"
        class="pt-search"
        type="search"
        placeholder="모델명 또는 제공업체 검색…"
        aria-label="모델 검색"
      />

      <div class="pt-unit" role="group" aria-label="가격 단위">
        <button
          :class="{ active: unit === '1m' }"
          @click="unit = '1m'"
        >
          1M 토큰
        </button>
        <button
          :class="{ active: unit === '1k' }"
          @click="unit = '1k'"
        >
          1K 토큰
        </button>
      </div>

      <button class="pt-csv" @click="exportCsv">CSV 내보내기</button>
      <button class="pt-reset" @click="resetFilters">초기화</button>
    </div>

    <!-- provider 필터 -->
    <div class="pt-providers">
      <label
        v-for="p in providers"
        :key="p"
        class="pt-chip"
        :class="{ on: isProviderActive(p) }"
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

    <div class="pt-meta">
      {{ filteredRows.length }}개 모델 · 단위: {{ unitLabel }}
    </div>

    <!-- 표 -->
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
            <th class="num sortable" @click="setSort('contextWindow')">
              컨텍스트<span class="ind">{{ sortIndicator('contextWindow') }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in filteredRows"
            :key="r.provider + '/' + r.model"
            :class="{ cheap: isCheapest(r) }"
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
              <a v-if="r.sourceUrl" :href="r.sourceUrl" target="_blank" rel="noopener">
                {{ r.model }}
              </a>
              <span v-else>{{ r.model }}</span>
            </td>
            <td class="num">
              {{ fmtPrice(r.inputPer1m) }}
              <span v-if="isCheapest(r)" class="pt-tag">최저</span>
            </td>
            <td class="num">{{ fmtPrice(r.outputPer1m) }}</td>
            <td class="num">{{ fmtContext(r.contextWindow) }}</td>
          </tr>
          <tr v-if="filteredRows.length === 0">
            <td colspan="5" class="pt-empty">조건에 맞는 모델이 없습니다.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.pt {
  margin: 1rem 0 2rem;
}

.pt-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.75rem;
}

.pt-search {
  flex: 1 1 240px;
  min-width: 0;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-size: 0.9rem;
}
.pt-search:focus {
  outline: none;
  border-color: var(--vp-c-brand-1);
}

.pt-unit {
  display: inline-flex;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  overflow: hidden;
}
.pt-unit button {
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-2);
  border: none;
  cursor: pointer;
}
.pt-unit button.active {
  background: var(--vp-c-brand-1);
  color: #fff;
}

.pt-csv,
.pt-reset {
  padding: 0.5rem 0.85rem;
  font-size: 0.85rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  cursor: pointer;
}
.pt-csv:hover,
.pt-reset:hover {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}

.pt-providers {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
}
.pt-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.6rem;
  font-size: 0.8rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  cursor: pointer;
  user-select: none;
  opacity: 0.5;
}
.pt-chip.on {
  opacity: 1;
  border-color: var(--c);
}
.pt-chip input {
  display: none;
}
.pt-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--c);
}

.pt-meta {
  font-size: 0.8rem;
  color: var(--vp-c-text-2);
  margin-bottom: 0.5rem;
}

.pt-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
}
.pt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.pt-table th,
.pt-table td {
  padding: 0.55rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--vp-c-divider);
  white-space: nowrap;
}
.pt-table thead th {
  position: sticky;
  top: 0;
  background: var(--vp-c-bg-soft);
  font-weight: 600;
  z-index: 1;
}
.pt-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
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
.pt-table tbody tr:hover {
  background: var(--vp-c-bg-soft);
}
.pt-table tr.cheap {
  background: color-mix(in srgb, var(--vp-c-brand-1) 8%, transparent);
}
.pt-table td.model a {
  color: var(--vp-c-text-1);
  text-decoration: none;
}
.pt-table td.model a:hover {
  color: var(--vp-c-brand-1);
  text-decoration: underline;
}

.pt-badge {
  display: inline-block;
  padding: 0.12rem 0.5rem;
  border-radius: 6px;
  color: #fff;
  font-size: 0.74rem;
  font-weight: 600;
}
.pt-tag {
  margin-left: 0.35rem;
  padding: 0.05rem 0.35rem;
  font-size: 0.68rem;
  border-radius: 4px;
  background: var(--vp-c-brand-1);
  color: #fff;
}
.pt-empty {
  text-align: center;
  color: var(--vp-c-text-2);
  padding: 1.5rem;
}

@media (max-width: 640px) {
  .pt-controls {
    gap: 0.4rem;
  }
  .pt-search {
    flex-basis: 100%;
  }
  .pt-table th,
  .pt-table td {
    padding: 0.45rem 0.55rem;
    font-size: 0.82rem;
  }
}
</style>
