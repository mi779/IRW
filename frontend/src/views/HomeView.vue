<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const cards: { title: string; description: string; route: string; color: string }[] = [
  {
    title: '单词管理',
    description: '维护单词库，添加、编辑或删除单词及其释义、词根、前后缀等信息。',
    route: '/words',
    color: '#e6f4ff',
  },
  {
    title: '词根分组学习',
    description: '通过词根关系图可视化地学习一组同根单词，加速记忆。',
    route: '/roots',
    color: '#fff7e6',
  },
  {
    title: '复习',
    description: '基于间隔重复（SRS）的复习队列，巩固长期记忆。',
    route: '/review',
    color: '#f6ffed',
  },
]

function navigate(route: string) {
  router.push(route)
}
</script>

<template>
  <main class="home-view">
    <div class="hero">
      <h1 class="title">IRW 词汇学习</h1>
      <p class="subtitle">基于词根 · 前缀 · 后缀的智能单词记忆系统</p>
    </div>
    <el-row :gutter="20" class="card-row">
      <el-col v-for="card in cards" :key="card.route" :xs="24" :sm="8">
        <el-card shadow="hover" class="nav-card" :body-style="{ padding: '24px' }" @click="navigate(card.route)">
          <div class="card-inner" :style="{ backgroundColor: card.color }">
            <h3 class="card-title">{{ card.title }}</h3>
            <p class="card-desc">{{ card.description }}</p>
            <div class="card-action">进入 →</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </main>
</template>

<style scoped>
.home-view {
  padding: 20px 0;
}

.hero {
  text-align: center;
  padding: 40px 0 32px;
}

.title {
  font-size: 32px;
  margin: 0 0 12px 0;
  color: #303133;
}

.subtitle {
  color: #909399;
  font-size: 16px;
  margin: 0;
}

.card-row {
  margin-top: 20px;
}

.nav-card {
  cursor: pointer;
  transition: transform 0.2s;
  border: none;
}

.nav-card:hover {
  transform: translateY(-4px);
}

.card-inner {
  border-radius: 8px;
  padding: 24px;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.card-title {
  font-size: 20px;
  margin: 0 0 12px 0;
  color: #303133;
}

.card-desc {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  flex: 1;
}

.card-action {
  color: #409eff;
  font-size: 14px;
  font-weight: 500;
  margin-top: 12px;
}
</style>
