import { createRouter, createWebHistory } from 'vue-router'

// Pages are loaded only when visited, so the homepage stays light.
const routes = [
  { path: '/', name: 'home', component: () => import('./pages/Landing.vue') },
  {
    path: '/app',
    component: () => import('./pages/app/AppLayout.vue'),
    children: [
      { path: '', name: 'overview', component: () => import('./pages/app/Overview.vue') },
      { path: 'disease', name: 'disease', component: () => import('./pages/app/Disease.vue') },
      { path: 'crop', name: 'crop', component: () => import('./pages/app/Crop.vue') },
      { path: 'assistant', name: 'assistant', component: () => import('./pages/app/Assistant.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: { name: 'home' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to) {
    if (to.hash) return { el: to.hash, behavior: 'smooth', top: 88 }
    return { top: 0 }
  },
})
