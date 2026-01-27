<script setup lang="ts">
/**
 * 全局 Toast 通知容器
 * 
 * 显示常驻的右上角报警通知。
 */
import { useAlertStore } from '@/stores/alert'
import AlertCard from '../business/AlertCard.vue'

const alertStore = useAlertStore()

const dismiss = (id: number) => {
  alertStore.removeToast(id)
}
</script>

<template>
  <div class="fixed top-4 right-4 z-50 flex flex-col gap-2 w-80 max-h-[90vh] overflow-y-auto pointer-events-none p-2 no-scrollbar">
    <TransitionGroup name="toast">
      <div 
        v-for="alert in alertStore.toasts" 
        :key="alert.id"
        class="pointer-events-auto shadow-lg rounded-lg overflow-hidden"
      >
        <AlertCard 
          :alert="alert"
          @dismiss="dismiss"
        />
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
