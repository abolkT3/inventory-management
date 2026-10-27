<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

const BUDGET_MIN = 0
const BUDGET_MAX = 100000
const BUDGET_STEP = 500
const DEBOUNCE_MS = 250

const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

const budget = ref(25000)
const recommendation = ref(null)
const loading = ref(true)
const error = ref(null)

const submitting = ref(false)
const placedOrder = ref(null)
const orderError = ref(null)

let debounceTimer = null
let requestCounter = 0

const items = computed(() => recommendation.value?.items ?? [])

const estimatedLeadTime = computed(() => {
  return items.value.reduce((max, item) => Math.max(max, Number(item.lead_time_days) || 0), 0)
})

const canPlaceOrder = computed(() => items.value.length > 0 && !submitting.value && !loading.value)

const money = (amount) => formatCurrency(Number(amount) || 0, currentCurrency.value)

const translateCategory = (category) => {
  const categoryMap = {
    'Circuit Boards': 'categories.circuitBoards',
    'Sensors': 'categories.sensors',
    'Actuators': 'categories.actuators',
    'Controllers': 'categories.controllers',
    'Power Supplies': 'categories.powerSupplies'
  }
  return categoryMap[category] ? t(categoryMap[category]) : category
}

const trendLabel = (trend) => {
  const key = `trends.${trend}`
  const label = t(key)
  return label === key ? trend : label
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString || ''
  const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
  return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
}

const loadRecommendations = async () => {
  const requestId = ++requestCounter
  loading.value = true
  error.value = null
  try {
    const result = await api.getRestockRecommendations(budget.value)
    // Ignore out-of-order responses
    if (requestId !== requestCounter) return
    recommendation.value = result
  } catch (err) {
    if (requestId !== requestCounter) return
    error.value = t('restocking.loadError')
    console.error('Failed to load recommendations:', err)
  } finally {
    if (requestId === requestCounter) loading.value = false
  }
}

watch(budget, () => {
  clearTimeout(debounceTimer)
  // Invalidate in-flight responses for the previous budget
  requestCounter++
  loading.value = true
  debounceTimer = setTimeout(loadRecommendations, DEBOUNCE_MS)
})

const placeOrder = async () => {
  if (!canPlaceOrder.value) return
  submitting.value = true
  orderError.value = null
  placedOrder.value = null
  try {
    placedOrder.value = await api.createRestockOrder({
      items: items.value.map(item => ({ sku: item.sku, quantity: item.quantity })),
      budget: budget.value
    })
  } catch (err) {
    const detail = err?.response?.data?.detail
    orderError.value = typeof detail === 'string' && detail
      ? detail
      : t('restocking.orderError')
    console.error('Failed to place restock order:', err)
  } finally {
    submitting.value = false
  }
}

onMounted(loadRecommendations)

onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
  // Invalidate any in-flight request
  requestCounter++
})
</script>

<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budget') }}</h3>
        <span class="budget-value">{{ money(budget) }}</span>
      </div>
      <input
        v-model.number="budget"
        type="range"
        class="budget-slider"
        :min="BUDGET_MIN"
        :max="BUDGET_MAX"
        :step="BUDGET_STEP"
        :aria-label="t('restocking.budgetLabel')"
      />
      <div class="slider-scale">
        <span>{{ money(BUDGET_MIN) }}</span>
        <span>{{ money(BUDGET_MAX) }}</span>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card info">
        <div class="stat-label">{{ t('restocking.summary.totalCost') }}</div>
        <div class="stat-value">{{ money(recommendation?.total_cost) }}</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">{{ t('restocking.summary.remainingBudget') }}</div>
        <div class="stat-value">{{ money(recommendation?.remaining_budget) }}</div>
      </div>
      <div class="stat-card warning">
        <div class="stat-label">{{ t('restocking.summary.leadTime') }}</div>
        <div class="stat-value">{{ t('restocking.summary.leadTimeDays', { days: estimatedLeadTime }) }}</div>
      </div>
    </div>

    <div v-if="placedOrder" class="confirmation" role="status">
      <strong>{{ t('restocking.orderPlaced') }}</strong>
      <span>
        {{ t('restocking.orderConfirmation', {
          orderNumber: placedOrder.order_number,
          date: formatDate(placedOrder.expected_delivery)
        }) }}
      </span>
      <router-link to="/orders" class="confirmation-link">{{ t('restocking.viewOrders') }}</router-link>
    </div>
    <div v-if="orderError" class="error" role="alert">{{ orderError }}</div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ items.length }})</h3>
        <button
          type="button"
          class="place-order-button"
          :disabled="!canPlaceOrder"
          @click="placeOrder"
        >
          {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
        </button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-else-if="loading && !recommendation" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="items.length === 0 && !loading" class="loading">{{ t('restocking.empty') }}</div>
      <div v-else class="table-container" :class="{ stale: loading }">
        <table>
          <thead>
            <tr>
              <th>{{ t('restocking.table.sku') }}</th>
              <th>{{ t('restocking.table.product') }}</th>
              <th>{{ t('restocking.table.category') }}</th>
              <th>{{ t('restocking.table.trend') }}</th>
              <th class="num">{{ t('restocking.table.onHand') }}</th>
              <th class="num">{{ t('restocking.table.forecast') }}</th>
              <th class="num">{{ t('restocking.table.shortfall') }}</th>
              <th class="num">{{ t('restocking.table.quantity') }}</th>
              <th class="num">{{ t('restocking.table.unitCost') }}</th>
              <th class="num">{{ t('restocking.table.lineTotal') }}</th>
              <th class="num">{{ t('restocking.table.leadTime') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.sku">
              <td><strong>{{ item.sku }}</strong></td>
              <td>{{ translateProductName(item.name) }}</td>
              <td>{{ translateCategory(item.category) }}</td>
              <td><span :class="['badge', item.trend]">{{ trendLabel(item.trend) }}</span></td>
              <td class="num">{{ item.quantity_on_hand.toLocaleString() }}</td>
              <td class="num">{{ item.forecasted_demand.toLocaleString() }}</td>
              <td class="num">{{ item.shortfall.toLocaleString() }}</td>
              <td class="num"><strong>{{ item.quantity.toLocaleString() }}</strong></td>
              <td class="num">{{ money(item.unit_cost) }}</td>
              <td class="num"><strong>{{ money(item.line_total) }}</strong></td>
              <td class="num">{{ t('restocking.leadTimeDays', { days: item.lead_time_days }) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
  cursor: pointer;
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  color: #64748b;
  font-size: 0.813rem;
}

.num {
  text-align: right;
  white-space: nowrap;
}

.stale {
  opacity: 0.6;
}

.place-order-button {
  padding: 0.5rem 1.25rem;
  border: 1px solid #0f172a;
  border-radius: 6px;
  background: #0f172a;
  color: #ffffff;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-button:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-button:disabled {
  background: #e2e8f0;
  border-color: #e2e8f0;
  color: #64748b;
  cursor: not-allowed;
}

.place-order-button:focus-visible,
.confirmation-link:focus-visible,
.budget-slider:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.confirmation {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  padding: 1rem;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 8px;
  color: #065f46;
  font-size: 0.938rem;
}

.confirmation-link {
  color: #1e40af;
  font-weight: 600;
  text-decoration: underline;
}
</style>
