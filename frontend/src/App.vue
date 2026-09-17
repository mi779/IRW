<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { computed, onMounted, ref } from 'vue'
import request from '@/services/request'

const router = useRouter()
const route = useRoute()

const appVersion = __APP_VERSION__
const buildTime = __BUILD_TIME__
const backendVersion = ref('')

onMounted(async () => {
  try {
    const d = await request.get<unknown, { commit: string; started: string }>('/version')
    backendVersion.value = `v${d.commit} · 启动 ${d.started}`
  } catch {
    backendVersion.value = ''
  }
})

const navItems = [
  { path: '/', label: '首页', icon: '🏠' },
  { path: '/words', label: '单词管理', icon: '📚' },
  { path: '/roots', label: '词根分组', icon: '🌳' },
  { path: '/review', label: '复习', icon: '🎯' },
]

const activePath = computed(() => route.path)
function navigate(path: string) { router.push(path) }
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="header-inner">
        <div class="brand" @click="navigate('/')">
          <div class="brand-logo">IRW</div>
          <div class="brand-text">
            <span class="brand-title lg-gradient-text">Vocab</span>
            <span class="brand-sub">词根记忆</span>
          </div>
        </div>
        <nav class="nav-tabs">
          <button
            v-for="item in navItems"
            :key="item.path"
            class="nav-tab"
            :class="{ active: activePath === item.path }"
            @click="navigate(item.path)"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </button>
        </nav>
      </div>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
    <footer class="app-footer">
      <span>前端 v{{ appVersion }} · 构建 {{ buildTime }}</span>
      <span v-if="backendVersion" class="footer-sep">|</span>
      <span v-if="backendVersion">后端 {{ backendVersion }}</span>
    </footer>
  </div>
</template>

<style scoped>
.app-shell { position: relative; min-height: 100vh; max-width: 1200px; margin: 0 auto; padding: 0 24px 48px; }

.app-header { position: sticky; top: 16px; z-index: 100; padding-top: 16px; }

.header-inner {
  display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 12px 20px;
  background: var(--lg-glass-bg-strong);
  backdrop-filter: blur(20px) saturate(1.8); -webkit-backdrop-filter: blur(20px) saturate(1.8);
  border: var(--lg-glass-border); border-radius: var(--lg-radius-xl); box-shadow: var(--lg-glass-shadow);
}

.brand { display: flex; align-items: center; gap: 12px; cursor: pointer; transition: transform 0.3s ease; flex-shrink: 0; }
.brand:hover { transform: scale(1.02); }

.brand-logo {
  width: 42px; height: 42px; border-radius: 14px; background: var(--lg-gradient-primary);
  display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px; letter-spacing: 0.5px;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
}

.brand-text { display: flex; flex-direction: column; line-height: 1.1; }
.brand-title { font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }
.brand-sub { font-size: 11px; color: var(--lg-text-tertiary); font-weight: 500; }

.nav-tabs { display: flex; gap: 4px; padding: 4px; background: rgba(99, 102, 241, 0.06); border-radius: var(--lg-radius-pill); }

.nav-tab {
  display: flex; align-items: center; gap: 6px; padding: 8px 16px; border: none; background: transparent; border-radius: var(--lg-radius-pill);
  font-size: 14px; font-weight: 500; color: var(--lg-text-secondary); cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); font-family: inherit;
}

.nav-tab:hover { color: var(--lg-text-primary); background: rgba(255, 255, 255, 0.5); }

.nav-tab.active {
  background: white; color: var(--lg-text-primary);
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.15);
}

.nav-icon { font-size: 14px; }
.app-main { padding-top: 28px; position: relative; z-index: 1; }

.app-footer {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  margin-top: 32px; padding: 14px 0 6px; border-top: 1px dashed rgba(99, 102, 241, 0.12);
  font-size: 11.5px; color: var(--lg-text-tertiary); opacity: 0.8;
  font-variant-numeric: tabular-nums; letter-spacing: 0.2px;
}
.footer-sep { opacity: 0.4; }
</style>
