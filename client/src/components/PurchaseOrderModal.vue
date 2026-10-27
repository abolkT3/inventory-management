<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">{{ mode === 'view' ? 'Purchase Order' : 'Create Purchase Order' }}</h3>
            <button class="close-button" type="button" aria-label="Close" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="item-summary">
              <div class="item-name">{{ backlogItem.item_name }}</div>
              <div class="item-sku">SKU: {{ backlogItem.item_sku }}</div>
              <div class="item-shortage">Shortage: {{ shortage }} units</div>
            </div>

            <!-- View mode -->
            <template v-if="mode === 'view'">
              <div v-if="viewLoading" class="state-message">Loading purchase order...</div>
              <div v-else-if="viewError" class="error-message">{{ viewError }}</div>
              <div v-else-if="po" class="info-grid">
                <div v-for="row in poRows" :key="row.label" class="info-item" :class="{ wide: row.wide }">
                  <div class="info-label">{{ row.label }}</div>
                  <div class="info-value">
                    <span v-if="row.badge" class="badge" :class="row.badge">{{ row.value }}</span>
                    <template v-else>{{ row.value }}</template>
                  </div>
                </div>
              </div>
            </template>

            <!-- Create mode -->
            <form v-else id="po-form" class="po-form" novalidate @submit.prevent="submit">
              <div v-if="submitError" class="error-message">{{ submitError }}</div>

              <div class="form-field">
                <label for="po-supplier">Supplier name *</label>
                <input id="po-supplier" v-model="form.supplier_name" type="text" :class="{ invalid: errors.supplier_name }" />
                <div v-if="errors.supplier_name" class="field-error">{{ errors.supplier_name }}</div>
              </div>

              <div class="form-row">
                <div class="form-field">
                  <label for="po-quantity">Quantity *</label>
                  <input id="po-quantity" v-model="form.quantity" type="number" min="1" step="1" :class="{ invalid: errors.quantity }" />
                  <div v-if="errors.quantity" class="field-error">{{ errors.quantity }}</div>
                </div>
                <div class="form-field">
                  <label for="po-cost">Unit cost *</label>
                  <input id="po-cost" v-model="form.unit_cost" type="number" min="0" step="0.01" :class="{ invalid: errors.unit_cost }" />
                  <div v-if="errors.unit_cost" class="field-error">{{ errors.unit_cost }}</div>
                </div>
              </div>

              <div class="form-field">
                <label for="po-date">Expected delivery date *</label>
                <input id="po-date" v-model="form.expected_delivery_date" type="date" :min="todayString" :class="{ invalid: errors.expected_delivery_date }" />
                <div v-if="errors.expected_delivery_date" class="field-error">{{ errors.expected_delivery_date }}</div>
              </div>

              <div class="form-field">
                <label for="po-notes">Notes</label>
                <textarea id="po-notes" v-model="form.notes" rows="3"></textarea>
              </div>
            </form>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" type="button" @click="close">{{ mode === 'view' ? 'Close' : 'Cancel' }}</button>
            <button v-if="mode !== 'view'" class="btn-primary" type="submit" form="po-form" :disabled="submitting">
              {{ submitting ? 'Creating...' : 'Create PO' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { api } from '../api'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  backlogItem: { type: Object, default: null },
  mode: { type: String, default: 'create', validator: (v) => ['create', 'view'].includes(v) }
})

const emit = defineEmits(['close', 'po-created'])

const form = reactive({
  supplier_name: '',
  quantity: '',
  unit_cost: '',
  expected_delivery_date: '',
  notes: ''
})
const errors = reactive({})
const submitError = ref('')
const submitting = ref(false)

const po = ref(null)
const viewLoading = ref(false)
const viewError = ref('')

// Incremented on every open so late responses from a previous open are ignored
let requestToken = 0

const shortage = computed(() => {
  if (!props.backlogItem) return 0
  return Math.max(0, props.backlogItem.quantity_needed - props.backlogItem.quantity_available)
})

// Local-time YYYY-MM-DD (toISOString would shift the day for non-UTC users)
const todayString = computed(() => {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
})

const formatDate = (value) => {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (isNaN(date.getTime())) return 'N/A'
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

// Date-only strings (YYYY-MM-DD) parse as UTC; render them in UTC to avoid off-by-one days
const formatDateOnly = (value) => {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (isNaN(date.getTime())) return 'N/A'
  const utc = /^\d{4}-\d{2}-\d{2}$/.test(String(value))
  return date.toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric', ...(utc ? { timeZone: 'UTC' } : {})
  })
}

const money = (n) => {
  const num = Number(n)
  if (!isFinite(num)) return 'N/A'
  return num.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

const statusBadge = (status) => {
  const s = String(status || '').toLowerCase()
  if (['received', 'delivered', 'completed'].includes(s)) return 'success'
  if (['cancelled', 'canceled'].includes(s)) return 'danger'
  if (['pending', 'draft'].includes(s)) return 'warning'
  return 'info'
}

const poRows = computed(() => {
  if (!po.value) return []
  const p = po.value
  return [
    { label: 'PO ID', value: p.id },
    { label: 'Supplier', value: p.supplier_name },
    { label: 'Quantity', value: `${p.quantity} units` },
    { label: 'Unit Cost', value: money(p.unit_cost) },
    { label: 'Total', value: money(Number(p.quantity) * Number(p.unit_cost)) },
    { label: 'Expected Delivery', value: formatDateOnly(p.expected_delivery_date) },
    { label: 'Status', value: p.status || 'N/A', badge: statusBadge(p.status) },
    { label: 'Created', value: formatDate(p.created_date) },
    { label: 'Notes', value: p.notes || 'None', wide: true }
  ]
})

const resetState = () => {
  form.supplier_name = ''
  form.quantity = shortage.value > 0 ? String(shortage.value) : ''
  form.unit_cost = ''
  form.expected_delivery_date = ''
  form.notes = ''
  Object.keys(errors).forEach((k) => delete errors[k])
  submitError.value = ''
  submitting.value = false
  po.value = null
  viewError.value = ''
  viewLoading.value = false
}

// Best-effort prefill of unit cost from the matching inventory item; never blocks the form
const prefillUnitCost = async (token, sku) => {
  try {
    const items = await api.getInventory()
    if (token !== requestToken || form.unit_cost !== '') return
    const match = Array.isArray(items) ? items.find((i) => i.sku === sku) : null
    if (match && isFinite(Number(match.unit_cost))) form.unit_cost = String(match.unit_cost)
  } catch (err) {
    // Prefill is optional; ignore failures
  }
}

const loadPO = async (token, backlogId) => {
  viewLoading.value = true
  try {
    const data = await api.getPurchaseOrderByBacklogItem(backlogId)
    if (token !== requestToken) return
    po.value = data
  } catch (err) {
    if (token !== requestToken) return
    viewError.value = err.response?.status === 404
      ? 'No purchase order found for this item.'
      : (err.response?.data?.detail || 'Failed to load purchase order.')
  } finally {
    if (token === requestToken) viewLoading.value = false
  }
}

// Reset and (re)load each time the modal opens or switches item/mode
watch(
  () => [props.isOpen, props.backlogItem?.id, props.mode],
  () => {
    requestToken++
    if (!props.isOpen || !props.backlogItem) return
    resetState()
    if (props.mode === 'view') {
      loadPO(requestToken, props.backlogItem.id)
    } else {
      prefillUnitCost(requestToken, props.backlogItem.item_sku)
    }
  },
  { immediate: true }
)

const validate = () => {
  Object.keys(errors).forEach((k) => delete errors[k])

  if (!form.supplier_name.trim()) errors.supplier_name = 'Supplier name is required.'

  const qty = Number(form.quantity)
  if (form.quantity === '' || form.quantity === null || !Number.isInteger(qty) || qty <= 0) {
    errors.quantity = 'Quantity must be a whole number greater than 0.'
  }

  const cost = Number(form.unit_cost)
  if (form.unit_cost === '' || form.unit_cost === null || !isFinite(cost) || cost < 0) {
    errors.unit_cost = 'Unit cost must be 0 or greater.'
  }

  if (!form.expected_delivery_date) {
    errors.expected_delivery_date = 'Expected delivery date is required.'
  } else if (isNaN(new Date(form.expected_delivery_date).getTime())) {
    errors.expected_delivery_date = 'Enter a valid date.'
  } else if (form.expected_delivery_date < todayString.value) {
    // ISO date strings compare correctly as plain strings
    errors.expected_delivery_date = 'Delivery date cannot be in the past.'
  }

  return Object.keys(errors).length === 0
}

const submit = async () => {
  if (submitting.value || !validate()) return
  submitError.value = ''
  submitting.value = true
  const token = requestToken
  try {
    const created = await api.createPurchaseOrder({
      backlog_item_id: props.backlogItem.id,
      supplier_name: form.supplier_name.trim(),
      quantity: Number(form.quantity),
      unit_cost: Number(form.unit_cost),
      expected_delivery_date: form.expected_delivery_date,
      notes: form.notes.trim()
    })
    emit('po-created', created)
  } catch (err) {
    if (token !== requestToken) return
    submitError.value = err.response?.data?.detail || 'Failed to create purchase order.'
  } finally {
    if (token === requestToken) submitting.value = false
  }
}

const close = () => {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem;
}

.item-summary {
  padding: 1rem 1.25rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.item-name {
  font-size: 1.063rem;
  font-weight: 700;
  color: #0f172a;
}

.item-sku {
  font-size: 0.813rem;
  color: #64748b;
  font-family: 'Monaco', 'Courier New', monospace;
  margin-top: 0.25rem;
}

.item-shortage {
  font-size: 0.875rem;
  font-weight: 600;
  color: #dc2626;
  margin-top: 0.5rem;
}

.po-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-field label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.form-field input,
.form-field textarea {
  padding: 0.625rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.938rem;
  font-family: inherit;
  color: #0f172a;
  background: white;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: #64748b;
  box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.15);
}

.form-field input.invalid {
  border-color: #dc2626;
}

.field-error {
  font-size: 0.813rem;
  color: #dc2626;
}

.error-message {
  padding: 0.75rem 1rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #991b1b;
  font-size: 0.875rem;
}

.state-message {
  padding: 1.5rem 0;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  min-width: 0;
}

.info-item.wide {
  grid-column: 1 / -1;
}

.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.info-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: capitalize;
}

.badge.success { background: #dcfce7; color: #166534; }
.badge.info { background: #dbeafe; color: #1e40af; }
.badge.warning { background: #fef3c7; color: #92400e; }
.badge.danger { background: #fecaca; color: #991b1b; }

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary,
.btn-primary {
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #334155;
}

.btn-secondary:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

.btn-primary {
  background: #0f172a;
  border: 1px solid #0f172a;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1e293b;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
