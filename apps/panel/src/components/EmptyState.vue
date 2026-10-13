<script setup>
import AppIcon from './AppIcon.vue'
defineProps({ title: String, description: String, compact: Boolean, icon: { type: String, default: 'message' } })
</script>

<template>
  <div class="empty-state" :class="{ 'empty-state--compact': compact }">
    <AppIcon :name="icon" :size="compact ? 43 : 59" />
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>
