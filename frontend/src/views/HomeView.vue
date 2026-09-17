<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
const cards = [
  { title: '单词管理', description: '维护单词库，添加、编辑或删除单词及其释义、词根、前后缀等信息。', route: '/words', icon: '📖', accent: 'linear-gradient(135deg, #6366f1, #8b5cf6)' },
  { title: '词根分组学习', description: '通过词根关系图可视化地学习一组同根单词，加速记忆。', route: '/roots', icon: '🌳', accent: 'linear-gradient(135deg, #f59e0b, #ec4899)' },
  { title: '复习', description: '基于间隔重复（SRS）的复习队列，巩固长期记忆。', route: '/review', icon: '🎯', accent: 'linear-gradient(135deg, #10b981, #22d3ee)' },
]
function navigate(route: string) { router.push(route) }
</script>

<template>
  <div class="home-view">
    <section class="hero">
      <div class="hero-badge"><span class="badge-dot"></span>Liquid Glass Design</div>
      <h1 class="hero-title"><span class="lg-gradient-text">IRW 词汇学习</span></h1>
      <p class="hero-subtitle">基于词根 · 前缀 · 后缀的智能单词记忆系统</p>
      <div class="hero-cta">
        <button class="btn-primary" @click="navigate('/words')">开始学习 →</button>
        <button class="btn-secondary" @click="navigate('/review')">今日复习</button>
      </div>
    </section>
    <section class="cards-section">
      <div v-for="card in cards" :key="card.route" class="feature-card lg-glass lg-hover-lift" @click="navigate(card.route)">
        <div class="card-icon" :style="{ background: card.accent }">{{ card.icon }}</div>
        <div class="card-content">
          <h3 class="card-title">{{ card.title }}</h3>
          <p class="card-desc">{{ card.description }}</p>
        </div>
        <div class="card-arrow">→</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-view { padding: 8px 0 24px; }
.hero { text-align: center; padding: 48px 24px 40px; margin-bottom: 16px; }
.hero-badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 16px; background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.15); border-radius: var(--lg-radius-pill); font-size: 12px; font-weight: 500; color: var(--lg-info); margin-bottom: 20px; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.badge-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--lg-info); box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2); animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
.hero-title { font-size: 44px; font-weight: 700; letter-spacing: -0.03em; margin: 0 0 12px; line-height: 1.1; }
.hero-subtitle { font-size: 16px; color: var(--lg-text-secondary); margin: 0; font-weight: 400; }
.hero-cta { display: flex; justify-content: center; gap: 12px; margin-top: 28px; }
.btn-primary { display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px; border: none; border-radius: var(--lg-radius-pill); background: var(--lg-gradient-primary); color: white; font-size: 15px; font-weight: 600; font-family: inherit; cursor: pointer; box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35); transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(99, 102, 241, 0.45); }
.btn-secondary { display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px; border: 1px solid rgba(99, 102, 241, 0.2); border-radius: var(--lg-radius-pill); background: rgba(255, 255, 255, 0.5); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); color: var(--lg-text-primary); font-size: 15px; font-weight: 600; font-family: inherit; cursor: pointer; transition: all 0.3s ease; }
.btn-secondary:hover { background: rgba(255, 255, 255, 0.75); border-color: rgba(99, 102, 241, 0.35); transform: translateY(-2px); }
.cards-section { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; padding: 8px 0; }
@media (max-width: 768px) { .cards-section { grid-template-columns: 1fr; } }
.feature-card { display: flex; align-items: center; gap: 16px; padding: 24px; cursor: pointer; border-radius: var(--lg-radius-lg); }
.card-icon { width: 52px; height: 52px; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08); }
.card-content { flex: 1; min-width: 0; }
.card-title { font-size: 17px; font-weight: 600; color: var(--lg-text-primary); margin: 0 0 6px; }
.card-desc { font-size: 13px; color: var(--lg-text-secondary); line-height: 1.55; margin: 0; }
.card-arrow { width: 36px; height: 36px; border-radius: 50%; background: rgba(99, 102, 241, 0.08); display: flex; align-items: center; justify-content: center; color: var(--lg-info); flex-shrink: 0; transition: all 0.3s ease; font-weight: bold; }
.feature-card:hover .card-arrow { background: var(--lg-gradient-primary); color: white; transform: translateX(4px); }
</style>
