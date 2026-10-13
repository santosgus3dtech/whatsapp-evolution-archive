<script setup>
import AppIcon from './AppIcon.vue'
import EmptyState from './EmptyState.vue'
import PageControls from './PageControls.vue'
import PhotoAvatar from './PhotoAvatar.vue'
import { chatLabel, formatCount, formatTime, mediaLabel } from '../lib/format'
defineProps({ page: Object, query: String, selectedChat: String, busy: Boolean, newOnly: Boolean, archived: Boolean, favoritesOnly: Boolean, label: String, labels: Array })
defineEmits(['update:query', 'update:favoritesOnly', 'update:label', 'select', 'page'])
</script>

<template>
  <section class="conversation-list" aria-label="Lista de conversas" :aria-busy="busy">
    <div class="conversation-list__toolbar">
      <div class="search-field">
        <AppIcon name="search" :size="21" />
        <input
          :value="query" type="search" placeholder="Buscar conversa" aria-label="Buscar conversa"
          @input="$emit('update:query', $event.target.value)"
        />
      </div>
      <div class="conversation-list__count">
        <span>{{ formatCount(page.total) }} {{ page.total === 1 ? 'conversa' : 'conversas' }}</span>
        <AppIcon v-if="busy" name="loading" class="spin" :size="16" />
      </div>
      <div class="conversation-filters">
        <button class="filter-button" :class="{ 'filter-button--active': favoritesOnly }" :aria-pressed="favoritesOnly" @click="$emit('update:favoritesOnly', !favoritesOnly)"><AppIcon name="star" :size="15" />Favoritos</button>
        <select :value="label" aria-label="Filtrar por etiqueta" @change="$emit('update:label', $event.target.value)"><option value="">Todas as etiquetas</option><option v-for="item in labels" :key="item" :value="item">{{ item }}</option></select>
      </div>
    </div>
    <div class="conversation-list__rows">
      <EmptyState
        v-if="!page.items.length"
        compact :icon="newOnly ? 'bell' : 'message'"
        :title="query || favoritesOnly || label ? 'Nenhuma conversa encontrada' : newOnly ? 'Você está em dia' : archived ? 'Nenhuma conversa arquivada' : 'Nenhuma conversa ainda'"
        :description="query || favoritesOnly || label ? 'Tente outro filtro para encontrar sua conversa.' : newOnly ? 'As novas mensagens recebidas aparecerão aqui.' : archived ? 'As conversas arquivadas neste painel aparecerão aqui.' : 'As conversas aparecerão após a sincronização.'"
      />
      <button
        v-for="conversation in page.items" :key="conversation.chat" class="conversation-row"
        :class="{ 'conversation-row--selected': selectedChat === conversation.chat }"
        :aria-pressed="selectedChat === conversation.chat"
        @click="$emit('select', conversation.chat)"
      >
        <PhotoAvatar :chat="conversation.chat" :name="chatLabel(conversation)" />
        <span class="conversation-row__content">
          <span class="conversation-row__line"><strong>{{ chatLabel(conversation) }}</strong><AppIcon v-if="conversation.favorite" name="star" class="favorite-star" :size="13" /><time>{{ formatTime(conversation.last_message_at) }}</time></span>
          <span class="conversation-row__line"><span class="conversation-preview">{{ conversation.last_text || mediaLabel(conversation.last_type) }}</span><span v-if="conversation.unseen > 0" class="unseen-count">{{ formatCount(conversation.unseen) }}</span></span>
          <span v-if="conversation.labels?.length" class="conversation-labels"><span v-for="item in conversation.labels.slice(0, 3)" :key="item" :title="item">{{ item }}</span></span>
        </span>
      </button>
    </div>
    <PageControls :page="page.page" :pages="page.pages" :busy="busy" @change="$emit('page', $event)" />
  </section>
</template>
