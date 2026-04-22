<template>
  <div class="container-fluid py-4">
    <!-- Header -->
    <div class="d-flex align-items-center mb-3 gap-3">
      <RouterLink to="/materials" class="btn btn-sm btn-outline-secondary">← Back</RouterLink>
      <div v-if="material">
        <h1 class="h5 mb-0">{{ material.title }}</h1>
        <small class="text-muted">
          {{ material.source_type }} ·
          {{ material.language }} ·
          <span :class="statusBadge(material.status)">{{ material.status }}</span>
          <span v-if="material.duration"> · {{ fmtDuration(material.duration) }}</span>
        </small>
      </div>
    </div>

    <!-- Toast -->
    <div class="position-fixed top-0 end-0 p-3" style="z-index:9999">
      <div v-if="toast" :class="`alert alert-${toast.type} mb-0 shadow`">{{ toast.message }}</div>
    </div>

    <!-- Processing indicator -->
    <div class="alert alert-info d-flex align-items-center gap-2" v-if="material?.status === 'processing' || material?.status === 'pending'">
      <span class="spinner-border spinner-border-sm"></span>
      Processing... <button class="btn btn-sm btn-outline-info ms-2" @click="loadMaterial">Refresh</button>
    </div>
    <div class="alert alert-danger" v-if="material?.status === 'failed'">
      Processing failed: {{ material.error_msg }}
    </div>

    <!-- Bulk push buttons -->
    <div class="d-flex gap-2 mb-3" v-if="segments.length">
      <button class="btn btn-sm btn-outline-primary" @click="bulkPush('anki')" :disabled="pushing" id="btn-bulk-anki">
        Push All → Anki
      </button>
      <button class="btn btn-sm btn-outline-info" @click="bulkPush('telegram')" :disabled="pushing" id="btn-bulk-telegram">
        Push All → Telegram
      </button>
    </div>

    <!-- Segments -->
    <div v-if="loading" class="text-center py-5">
      <span class="spinner-border"></span>
    </div>
    <div v-else-if="!segments.length && material?.status === 'done'" class="text-muted text-center py-5">
      No segments generated.
    </div>

    <div class="card mb-3 shadow-sm" v-for="seg in segments" :key="seg.id">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <span class="badge bg-secondary me-2">#{{ seg.index }}</span>
          <span class="badge bg-light text-dark ms-auto">{{ seg.audio_source_type }}</span>
        </div>

        <!-- Audio player -->
        <audio controls class="w-100 mb-2" :src="`/api/audio/${seg.id}`" preload="none">
          Your browser does not support audio.
        </audio>

        <!-- Text editing -->
        <div v-if="editingId !== seg.id">
          <p class="mb-1">{{ seg.text }}</p>
          <p class="text-muted small mb-1" v-if="seg.translation">{{ seg.translation }}</p>
          <small class="text-muted" v-if="seg.start_time !== null">
            {{ fmtTime(seg.start_time) }} – {{ fmtTime(seg.end_time) }}
          </small>
        </div>
        <div v-else>
          <textarea v-model="editForm.text" class="form-control mb-2" rows="2"></textarea>
          <input v-model="editForm.translation" class="form-control mb-2" placeholder="Chinese translation (optional)" />
          <div class="d-flex gap-1">
            <button class="btn btn-sm btn-success" @click="saveEdit(seg)">Save</button>
            <button class="btn btn-sm btn-secondary" @click="editingId = null">Cancel</button>
          </div>
        </div>

        <!-- Action buttons -->
        <div class="d-flex gap-2 mt-2 flex-wrap">
          <button class="btn btn-sm btn-outline-secondary" @click="startEdit(seg)" :id="`btn-edit-${seg.id}`">Edit</button>
          <button class="btn btn-sm btn-outline-primary" @click="pushSeg(seg, 'anki')" :disabled="pushing" :id="`btn-anki-${seg.id}`">
            Anki
          </button>
          <button class="btn btn-sm btn-outline-info" @click="pushSeg(seg, 'telegram')" :disabled="pushing" :id="`btn-telegram-${seg.id}`">
            Telegram
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { materialsApi, segmentsApi } from '../api/index.js'

const route = useRoute()
const materialId = Number(route.params.id)

const material = ref(null)
const segments = ref([])
const loading = ref(false)
const pushing = ref(false)
const toast = ref(null)
const editingId = ref(null)
const editForm = ref({ text: '', translation: '' })

async function loadMaterial() {
  const res = await materialsApi.get(materialId)
  material.value = res.data
}

async function loadSegments() {
  loading.value = true
  try {
    const res = await materialsApi.getSegments(materialId)
    segments.value = res.data
  } finally {
    loading.value = false
  }
}

async function pushSeg(seg, platform) {
  pushing.value = true
  try {
    await segmentsApi.push(seg.id, platform)
    showToast(`Sent to ${platform}!`, 'success')
  } catch (e) {
    showToast(e.response?.data?.detail || `Push to ${platform} failed`, 'danger')
  } finally {
    pushing.value = false
  }
}

async function bulkPush(platform) {
  if (!confirm(`Push all ${segments.value.length} segments to ${platform}?`)) return
  pushing.value = true
  try {
    await materialsApi.push(materialId, platform)
    showToast(`All segments pushed to ${platform}!`, 'success')
  } catch (e) {
    showToast(e.response?.data?.detail || 'Bulk push failed', 'danger')
  } finally {
    pushing.value = false
  }
}

function startEdit(seg) {
  editingId.value = seg.id
  editForm.value = { text: seg.text, translation: seg.translation || '' }
}

async function saveEdit(seg) {
  try {
    const res = await segmentsApi.update(seg.id, editForm.value)
    const idx = segments.value.findIndex(s => s.id === seg.id)
    if (idx !== -1) segments.value[idx] = res.data
    editingId.value = null
    showToast('Saved', 'success')
  } catch {
    showToast('Save failed', 'danger')
  }
}

function statusBadge(status) {
  const map = {
    pending: 'badge bg-secondary', processing: 'badge bg-warning text-dark',
    done: 'badge bg-success', failed: 'badge bg-danger',
  }
  return map[status] || 'badge bg-light text-dark'
}

function fmtDuration(s) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}

function fmtTime(s) {
  if (s == null) return ''
  const m = Math.floor(s / 60), sec = (s % 60).toFixed(1)
  return `${m}:${String(Math.floor(s % 60)).padStart(2, '0')}.${sec.split('.')[1]}`
}

function showToast(msg, type = 'info') {
  toast.value = { message: msg, type }
  setTimeout(() => { toast.value = null }, 4000)
}

onMounted(async () => {
  await loadMaterial()
  await loadSegments()
})
</script>
