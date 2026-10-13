<script setup>
import AppIcon from './AppIcon.vue'
defineProps({ page: { type: Number, default: 1 }, pages: { type: Number, default: 1 }, busy: Boolean })
defineEmits(['change'])
</script>

<template>
  <div v-if="pages > 1" class="page-controls" aria-label="Paginação">
    <button class="icon-button" aria-label="Página anterior" :disabled="page <= 1 || busy" @click="$emit('change', page - 1)">
      <AppIcon name="previous" :size="18" />
    </button>
    <span>{{ page }} de {{ pages }}</span>
    <button class="icon-button" aria-label="Próxima página" :disabled="page >= pages || busy" @click="$emit('change', page + 1)">
      <AppIcon name="next" :size="18" />
    </button>
  </div>
</template>
