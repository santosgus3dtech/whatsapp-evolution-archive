<script setup>
import { ref, watch } from 'vue'
import { apiUrl, queryString } from '../lib/api'
const props = defineProps({ chat: String, name: String })
const unavailable = ref(false)
watch(() => props.chat, () => { unavailable.value = false })
</script>

<template>
  <span class="conversation-avatar">
    <img v-if="chat && !unavailable" :src="apiUrl('/api/conversations/photo?' + queryString({ chat }))" alt="" loading="lazy" decoding="async" @error="unavailable = true" />
    <span v-else aria-hidden="true">{{ (name || chat || 'C').slice(0, 1).toUpperCase() }}</span>
  </span>
</template>
