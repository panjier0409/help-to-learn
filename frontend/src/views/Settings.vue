<template>
  <div class="container py-4" style="max-width: 700px;">
    <h1 class="h4 mb-4">Settings</h1>

    <div class="alert alert-success" v-if="saved">Settings saved successfully.</div>
    <div class="alert alert-danger" v-if="error">{{ error }}</div>

    <form @submit.prevent="save">
      <!-- Anki -->
      <div class="card mb-4 shadow-sm">
        <div class="card-header"><strong>🃏 Anki</strong></div>
        <div class="card-body">
          <div class="mb-3">
            <label class="form-label">Deck Name</label>
            <input v-model="form.anki_deck_name" type="text" class="form-control"
                   placeholder="English::Listening" id="input-anki-deck" />
            <div class="form-text">Make sure this deck exists in Anki or it will be created.</div>
          </div>
        </div>
      </div>

      <!-- Telegram -->
      <div class="card mb-4 shadow-sm">
        <div class="card-header"><strong>✈️ Telegram</strong></div>
        <div class="card-body">
          <div class="mb-3">
            <label class="form-label">Your Chat ID</label>
            <input v-model="form.telegram_chat_id" type="text" class="form-control"
                   placeholder="e.g. 123456789" id="input-telegram-chat" />
            <div class="form-text">
              Send /start to your bot, then get the Chat ID from
              <code>https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates</code>.
            </div>
          </div>
        </div>
      </div>

      <!-- TTS / STT -->
      <div class="card mb-4 shadow-sm">
        <div class="card-header"><strong>🔊 TTS / STT Worker</strong></div>
        <div class="card-body">
          <div class="mb-3">
            <label class="form-label">Worker URL</label>
            <input v-model="form.tts_worker_url" type="url" class="form-control"
                   placeholder="https://your-worker.workers.dev" id="input-tts-url" />
            <div class="form-text">Your deployed wangwangit/tts Cloudflare Worker URL.</div>
          </div>
          <div class="mb-3">
            <label class="form-label">SiliconFlow Token (for STT)</label>
            <input v-model="form.tts_token" type="password" class="form-control"
                   placeholder="Leave empty to use server default" id="input-tts-token" />
          </div>
        </div>
      </div>

      <button type="submit" class="btn btn-primary" :disabled="saving" id="btn-save-settings">
        <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
        Save Settings
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usersApi } from '../api/index.js'

const form = ref({
  anki_deck_name: '',
  telegram_chat_id: '',
  tts_worker_url: '',
  tts_token: '',
})
const saving = ref(false)
const saved = ref(false)
const error = ref('')

async function load() {
  try {
    const res = await usersApi.me()
    const u = res.data
    form.value = {
      anki_deck_name:   u.anki_deck_name || 'English::Listening',
      telegram_chat_id: u.telegram_chat_id || '',
      tts_worker_url:   u.tts_worker_url || '',
      tts_token:        '',  // Never pre-fill token
    }
  } catch {}
}

async function save() {
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    const payload = { ...form.value }
    if (!payload.tts_token) delete payload.tts_token  // Don't overwrite with empty
    await usersApi.update(payload)
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Save failed'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
