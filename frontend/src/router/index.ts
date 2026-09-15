import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // this is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue'),
    },
    {
      path: '/words',
      name: 'words',
      component: () => import('@/views/DictWordsView.vue'),
    },
    {
      path: '/affixes',
      name: 'affixes',
      component: () => import('@/views/WordsView.vue'),
    },
    {
      path: '/roots',
      name: 'roots',
      component: () => import('@/views/RootsView.vue'),
    },
    {
      path: '/review',
      name: 'review',
      component: () => import('@/views/ReviewView.vue'),
    },
  ],
})

export default router
