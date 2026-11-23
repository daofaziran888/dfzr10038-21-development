import { createRouter, createWebHistory } from 'vue-router'

import Overview from '@/views/Overview.vue'
import RejectionWorkbench from '@/views/RejectionWorkbench.vue'
import WorkbenchView from '@/views/WorkbenchView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: Overview },
    { path: '/rejection', name: 'rejection', component: RejectionWorkbench },
    { path: '/:moduleKey', name: 'module', component: WorkbenchView, props: true },
  ],
})

export default router
