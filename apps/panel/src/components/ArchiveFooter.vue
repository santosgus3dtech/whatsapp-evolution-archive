<script setup>
import AppIcon from './AppIcon.vue'
</script>

<template>
  <footer class="archive-footer">
    <div class="archive-footer__coverage">
      <AppIcon name="info" :size="22" />
      <div>
        <span>Histórico disponível</span>
        <p>A sincronização não garante todas as conversas antigas.</p>
      </div>
    </div>
    <p class="archive-footer__media">Integração com Evolution API · Mídia reservada para uma próxima fase.</p>
  </footer>
</template>
