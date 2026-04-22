<template>
  <div class="share-page">
    <!-- Header bar -->
    <header class="share-header">
      <span class="share-logo">📚 Help to Learn</span>
      <span class="share-badge">Public Share</span>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="share-loading">
      <span class="spinner"></span>
      <span>Loading…</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="share-error">
      <p>{{ error }}</p>
    </div>

    <!-- Content -->
    <main v-else class="share-content">
      <!-- Material info -->
      <div class="material-info">
        <h1 class="material-title">{{ material.title }}</h1>
        <div class="material-meta">
          <span class="meta-tag">{{ material.language }}</span>
          <span class="meta-tag">{{ material.source_type }}</span>
          <span v-if="material.duration" class="meta-tag">{{ fmtDuration(material.duration) }}</span>
        </div>
      </div>

      <!-- Segments -->
      <!-- Segments controls -->
      <div class="d-flex gap-2 mb-4" v-if="segments.length">
        <button class="btn-play-seq" v-if="!isSequencePlaying" @click="startSequence">
          ▶ Play Sequence
        </button>
        <button class="btn-pause-seq" v-else @click="pauseSequence">
          ⏸ Pause Sequence
        </button>
      </div>

      <div v-if="!segments.length" class="share-empty">No content available.</div>

      <div
        v-for="seg in segments"
        :key="seg.id"
        :id="`seg-${seg.id}`"
        class="segment-card"
        :class="{ highlighted: highlightedId === seg.id, playing: currentPlayingId === seg.id }"
      >
        <div class="seg-index">#{{ seg.index }}</div>

        <!-- Audio player -->
        <audio
          controls
          class="seg-audio"
          :src="`/api/audio/${seg.id}`"
          preload="metadata"
          :id="`audio-player-${seg.id}`"
          @play="onAudioPlay(seg.id)"
          @ended="onAudioEnded(seg.id)"
        >Your browser does not support audio.</audio>

        <!-- Text -->
        <p class="seg-text">{{ seg.text }}</p>
        <p v-if="seg.translation" class="seg-translation">{{ seg.translation }}</p>

        <!-- Timestamps -->
        <small v-if="seg.start_time != null" class="seg-time">
          {{ fmtTime(seg.start_time) }} – {{ fmtTime(seg.end_time) }}
        </small>

        <!-- Anchor copy button -->
        <button class="seg-link-btn" @click="copySegLink(seg.id)" :title="'Copy link to segment #' + seg.index">
          🔗
        </button>
      </div>
    </main>

    <!-- Copy toast -->
    <div v-if="copyToast" class="copy-toast">Link copied!</div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const materialId = Number(route.params.id)

const material = ref(null)
const segments = ref([])
const loading = ref(true)
const error = ref(null)
const highlightedId = ref(null)
const copyToast = ref(false)

// Audio sequence logic (same as MaterialDetail)
const isSequencePlaying = ref(false)
const currentPlayingId = ref(null)

function onAudioPlay(segId) {
  // Pause other players
  if (currentPlayingId.value && currentPlayingId.value !== segId) {
    const prev = document.getElementById(`audio-player-${currentPlayingId.value}`)
    if (prev) prev.pause()
  }
  currentPlayingId.value = segId
}

function onAudioEnded(segId) {
  if (isSequencePlaying.value) {
    const idx = segments.value.findIndex(s => s.id === segId)
    if (idx !== -1 && idx < segments.value.length - 1) {
      const nextSeg = segments.value[idx + 1]
      const nextAudio = document.getElementById(`audio-player-${nextSeg.id}`)
      if (nextAudio) {
        // Scroll to next segment
        nextAudio.scrollIntoView({ behavior: 'smooth', block: 'center' })
        nextAudio.play()
      }
    } else {
      isSequencePlaying.value = false
    }
  }
}

function startSequence() {
  isSequencePlaying.value = true
  // Start from first segment OR current playing
  let segToPlay = segments.value[0]
  if (currentPlayingId.value) {
    const currIdx = segments.value.findIndex(s => s.id === currentPlayingId.value)
    if (currIdx !== -1) segToPlay = segments.value[currIdx]
  }

  if (segToPlay) {
    const audio = document.getElementById(`audio-player-${segToPlay.id}`)
    if (audio) {
      audio.scrollIntoView({ behavior: 'smooth', block: 'center' })
      audio.play()
    }
  }
}

function pauseSequence() {
  isSequencePlaying.value = false
  if (currentPlayingId.value) {
    const audio = document.getElementById(`audio-player-${currentPlayingId.value}`)
    if (audio) audio.pause()
  }
}

async function load() {
  try {
    const [matRes, segRes] = await Promise.all([
      axios.get(`/api/share/${materialId}`),
      axios.get(`/api/share/${materialId}/segments`),
    ])
    material.value = matRes.data
    segments.value = segRes.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load content.'
  } finally {
    loading.value = false
  }
}

function scrollToAnchor() {
  const hash = window.location.hash  // e.g. "#seg-42"
  if (!hash) return
  const targetId = hash.slice(1)     // "seg-42"
  const segId = Number(targetId.replace('seg-', ''))
  highlightedId.value = segId

  nextTick(() => {
    const el = document.getElementById(targetId)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  })
}

function copySegLink(segId) {
  const url = `${window.location.origin}/share/${materialId}#seg-${segId}`
  navigator.clipboard.writeText(url).then(() => {
    copyToast.value = true
    setTimeout(() => { copyToast.value = false }, 2000)
  })
}

function fmtDuration(s) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}

function fmtTime(s) {
  if (s == null) return ''
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(1)
  return `${m}:${String(Math.floor(s % 60)).padStart(2, '0')}.${sec.split('.')[1]}`
}

onMounted(async () => {
  await load()
  scrollToAnchor()
})
</script>

<style scoped>
.share-page {
  min-height: 100vh;
  background: #0f1117;
  color: #e2e8f0;
  font-family: 'Inter', 'Segoe UI', sans-serif;
}

.share-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: #1a1d27;
  border-bottom: 1px solid #2d3248;
  position: sticky;
  top: 0;
  z-index: 100;
}

.share-logo {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.share-badge {
  font-size: 0.72rem;
  background: #3b82f6;
  color: #fff;
  border-radius: 20px;
  padding: 2px 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.share-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 0;
  color: #94a3b8;
}

.spinner {
  width: 22px;
  height: 22px;
  border: 3px solid #3b82f6;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.share-error {
  text-align: center;
  padding: 60px 24px;
  color: #f87171;
}

.share-content {
  max-width: 760px;
  margin: 0 auto;
  padding: 32px 16px 60px;
}

.material-info {
  margin-bottom: 28px;
}

.material-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 10px;
  line-height: 1.3;
}

.material-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-tag {
  font-size: 0.75rem;
  background: #1e2435;
  border: 1px solid #2d3248;
  border-radius: 6px;
  padding: 2px 10px;
  color: #94a3b8;
  font-weight: 500;
}

.btn-play-seq, .btn-pause-seq {
  padding: 8px 20px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-play-seq {
  background: #3b82f6;
  color: white;
}

.btn-play-seq:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.btn-pause-seq {
  background: #f59e0b;
  color: white;
}

.btn-pause-seq:hover {
  background: #d97706;
  transform: translateY(-1px);
}

.share-empty {
  text-align: center;
  color: #64748b;
  padding: 60px 0;
}

.segment-card {
  position: relative;
  background: #1a1d27;
  border: 1px solid #2d3248;
  border-radius: 12px;
  padding: 18px 18px 14px;
  margin-bottom: 16px;
  transition: border-color 0.3s, box-shadow 0.3s;
  scroll-margin-top: 80px;
}

.segment-card.highlighted {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.segment-card.playing {
  border-color: #3b82f6;
  background: #1e2435;
}

.seg-index {
  font-size: 0.72rem;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 10px;
  letter-spacing: 0.05em;
}

.seg-audio {
  width: 100%;
  margin-bottom: 12px;
  border-radius: 6px;
  height: 36px;
  filter: invert(0.1);
}

.seg-text {
  font-size: 1rem;
  line-height: 1.65;
  color: #e2e8f0;
  margin-bottom: 4px;
}

.seg-translation {
  font-size: 0.88rem;
  color: #94a3b8;
  margin-bottom: 4px;
}

.seg-time {
  font-size: 0.72rem;
  color: #475569;
}

.seg-link-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  opacity: 0.4;
  transition: opacity 0.2s;
  padding: 0;
  line-height: 1;
}

.seg-link-btn:hover {
  opacity: 1;
}

.copy-toast {
  position: fixed;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  background: #3b82f6;
  color: #fff;
  padding: 8px 22px;
  border-radius: 20px;
  font-size: 0.88rem;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(59,130,246,0.4);
  z-index: 9999;
  animation: fadein 0.2s ease;
}

@keyframes fadein {
  from { opacity: 0; transform: translateX(-50%) translateY(10px); }
  to   { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.d-flex { display: flex; }
.gap-2 { gap: 0.5rem; }
.mb-4 { margin-bottom: 1.5rem; }
</style>
