<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <el-menu
        mode="horizontal"
        :ellipsis="false"
        router
        :default-active="$route.path"
      >
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/words">单词管理</el-menu-item>
        <el-menu-item index="/roots">词根分组</el-menu-item>
        <el-menu-item index="/review">复习</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="app-main">
      <RouterView />
    </el-main>
  </el-container>
</template>

<style scoped>
.app-container {
  max-width: 1280px;
  margin: 0 auto;
}

.app-header {
  padding: 0;
  border-bottom: 1px solid var(--el-border-color-light);
}

.app-main {
  padding: 20px;
}
</style>
