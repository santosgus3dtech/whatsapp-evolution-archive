<script setup>
import AppIcon from './AppIcon.vue'
import BrandMark from './BrandMark.vue'
import { formatCount } from '../lib/format'
defineProps({ active: String, unseen: { type: Number, default: 0 }, open: Boolean })
defineEmits(['navigate', 'logout', 'close'])
const navigation = [
  { id: 'conversations', label: 'Conversas', icon: 'message' },
  { id: 'new', label: 'Novas mensagens', icon: 'bell' },
  { id: 'search', label: 'Busca global', icon: 'search' },
  { id: 'archived', label: 'Arquivadas', icon: 'archive' },
  { id: 'history', label: 'Histórico', icon: 'history' },
  { id: 'connection', label: 'Conexão', icon: 'connection' },
]
</script>

<template>
  <button v-if="open" class="sidebar-backdrop" aria-label="Fechar navegação" @click="$emit('close')" />
  <aside class="sidebar" :class="{ 'sidebar--open': open }" aria-label="WhatsNexo">
    <div class="sidebar__brand"><BrandMark dark /></div>
    <p class="sidebar__caption">WhatsNexo</p>
    <nav class="sidebar__navigation" aria-label="Navegação do WhatsNexo">
      <button
        v-for="item in navigation" :key="item.id" class="nav-item"
        :class="{ 'nav-item--active': active === item.id }"
        :aria-current="active === item.id ? 'page' : undefined"
        @click="$emit('navigate', item.id)"
      >
        <AppIcon :name="item.icon" :size="24" />
        <span>{{ item.label }}</span>
        <span v-if="item.id === 'new' && unseen > 0" class="nav-count">{{ formatCount(unseen) }}</span>
      </button>
    </nav>
    <div class="sidebar__bottom">
      <div class="nav-item sidebar__private"><AppIcon name="lock" :size="23" /><span>Acesso privado</span></div>
      <button class="nav-item" @click="$emit('logout')"><AppIcon name="logout" :size="23" /><span>Sair</span></button>
    </div>
  </aside>
</template>
