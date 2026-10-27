<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true">{{ brandInitial }}</span>
        <div v-show="!collapsed" class="brand-text">
          <span class="brand-name">{{ t('nav.companyName') }}</span>
          <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
        </div>
      </div>
      <button
        type="button"
        class="toggle-button"
        :aria-expanded="String(!collapsed)"
        aria-controls="sidebar-nav"
        :aria-label="t('nav.toggleSidebar')"
        :title="t('nav.toggleSidebar')"
        @click="toggle"
      >
        <svg
          class="toggle-icon"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.75"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M15 6l-6 6 6 6" />
        </svg>
      </button>
    </div>

    <nav id="sidebar-nav" :aria-label="t('nav.main')" class="sidebar-nav">
      <ul class="nav-list">
        <li v-for="item in navItems" :key="item.path">
          <router-link
            :to="item.path"
            class="nav-link"
            :title="collapsed ? t(item.labelKey) : undefined"
          >
            <svg
              class="nav-icon"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path :d="item.icon" />
            </svg>
            <span class="nav-label" :class="{ 'visually-hidden': collapsed }">{{ t(item.labelKey) }}</span>
          </router-link>
        </li>
      </ul>
    </nav>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from '../composables/useI18n'

const STORAGE_KEY = 'sidebar-collapsed'
const COLLAPSE_BREAKPOINT = 1024

const { t } = useI18n()

const navItems = [
  { path: '/', labelKey: 'nav.overview', icon: 'M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z' },
  { path: '/inventory', labelKey: 'nav.inventory', icon: 'M21 8l-9-5-9 5v8l9 5 9-5V8z M3 8l9 5 9-5 M12 13v8' },
  { path: '/orders', labelKey: 'nav.orders', icon: 'M8 6h12 M8 12h12 M8 18h12 M4 6h.01 M4 12h.01 M4 18h.01' },
  { path: '/restocking', labelKey: 'nav.restocking', icon: 'M3 7h13v10H3z M16 10h3l2 3v4h-5 M7 19.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z M17 19.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z' },
  { path: '/spending', labelKey: 'nav.finance', icon: 'M12 3v18 M16 7.5c0-1.5-1.8-2.5-4-2.5s-4 1-4 2.5 1.8 2.5 4 2.5 4 1 4 2.5-1.8 2.5-4 2.5-4-1-4-2.5' },
  { path: '/demand', labelKey: 'nav.demandForecast', icon: 'M3 17l6-6 4 4 8-8 M15 7h6v6' },
  { path: '/reports', labelKey: 'nav.reports', icon: 'M4 4v16h16 M8 16v-5 M12 16V8 M16 16v-3' }
]

// Read once at setup. Saved preference wins; otherwise collapse on narrow screens.
const readInitialState = () => {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    if (saved === 'true') return true
    if (saved === 'false') return false
  } catch (err) {
    // Storage unavailable (privacy mode, blocked); fall through to default
  }
  return typeof window !== 'undefined' && window.innerWidth < COLLAPSE_BREAKPOINT
}

const collapsed = ref(readInitialState())

const brandInitial = computed(() => (t('nav.companyName') || '').charAt(0))

const toggle = () => {
  collapsed.value = !collapsed.value
  try {
    window.localStorage.setItem(STORAGE_KEY, String(collapsed.value))
  } catch (err) {
    // Ignore storage errors; state still works for this session
  }
}
</script>

<style scoped>
.sidebar {
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  height: 100dvh;
  width: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-3);
  background: var(--color-text);
  color: #cbd5e1;
  overflow-x: hidden;
  overflow-y: auto;
  z-index: 200;
  transition: width 0.18s ease;
}

.sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

/* Collapsed: hide the brand mark so the header stays one row (toggle only) */
.sidebar.collapsed .sidebar-header {
  justify-content: center;
}

.sidebar.collapsed .brand {
  display: none;
}

.sidebar.collapsed .nav-link {
  justify-content: center;
  padding: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.brand-mark {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: #ffffff;
  color: var(--color-text);
  font-weight: 700;
  font-size: 1rem;
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  color: #ffffff;
  font-weight: 700;
  font-size: 0.938rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  color: #cbd5e1;
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toggle-button {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #cbd5e1;
  border: 1px solid #334155;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.toggle-button:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.toggle-icon {
  transition: transform 0.18s ease;
}

.sidebar.collapsed .toggle-icon {
  transform: rotate(180deg);
}

.nav-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 40px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-sm);
  color: #cbd5e1;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
  white-space: nowrap;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

/* router-link adds aria-current="page" on the exact active route */
.nav-link[aria-current="page"] {
  background: rgba(255, 255, 255, 0.14);
  color: #ffffff;
  font-weight: 700;
}

/* Non-color cue: left bar plus bolder weight */
.nav-link[aria-current="page"]::before {
  content: '';
  position: absolute;
  left: 0;
  top: var(--space-2);
  bottom: var(--space-2);
  width: 3px;
  border-radius: 2px;
  background: #60a5fa;
}

.nav-icon {
  flex-shrink: 0;
}

.toggle-button:focus-visible,
.nav-link:focus-visible {
  outline: 2px solid #93c5fd;
  outline-offset: 2px;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .toggle-icon {
    transition: none;
  }
}
</style>
