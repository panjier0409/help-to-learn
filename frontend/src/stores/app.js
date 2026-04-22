import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const toast = ref(null)  // { message, type: 'success'|'danger'|'warning'|'info' }

  function showToast(message, type = 'info') {
    toast.value = { message, type }
    setTimeout(() => { toast.value = null }, 4000)
  }

  return { toast, showToast }
})
