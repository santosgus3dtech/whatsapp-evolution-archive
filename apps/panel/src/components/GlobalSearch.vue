<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import EmptyState from './EmptyState.vue'
import PageControls from './PageControls.vue'
import PhotoAvatar from './PhotoAvatar.vue'
import ArchiveFooter from './ArchiveFooter.vue'
import { chatLabel, formatCount, formatDate, mediaLabel } from '../lib/format'
const props = defineProps({ page: Object, busy: Boolean, searched: Boolean, chatOptions: Array, optionsBusy: Boolean })
const emit = defineEmits(['search', 'page', 'open', 'chat-query'])
const query = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const chat = ref('')
const type = ref('')
const direction = ref('')
const chatQuery = ref('')
const chosenChat = ref(null)
const validation = ref('')
const filtersOpen = ref(false)
const activeFilters = computed(() => [dateFrom.value, dateTo.value, chat.value, type.value, direction.value].filter(Boolean).length)
let chatTimer
watch(chatQuery, value => { clearTimeout(chatTimer); chatTimer = setTimeout(() => emit('chat-query', value.trim()), 250) })
watch(chat, value => { chosenChat.value = props.chatOptions?.find(option => option.chat === value) || chosenChat.value })
const options = computed(() => chosenChat.value && !props.chatOptions?.some(option => option.chat === chosenChat.value.chat) ? [chosenChat.value, ...(props.chatOptions || [])] : props.chatOptions || [])
onBeforeUnmount(() => clearTimeout(chatTimer))
const types = ['text', 'image', 'video', 'audio', 'document', 'sticker', 'reaction', 'button', 'list', 'poll', 'contact', 'contacts', 'location', 'system', 'unknown']
function submit() {
  validation.value = ''
  const from = dateFrom.value ? Math.floor(new Date(dateFrom.value + 'T00:00:00').getTime() / 1000) : undefined
  const to = dateTo.value ? Math.floor(new Date(dateTo.value + 'T23:59:59').getTime() / 1000) : undefined
  if (from && to && from > to) { validation.value = 'A data final deve ser igual ou posterior à data inicial.'; return }
  emit('search', { q: query.value.trim(), date_from: from, date_to: to, chat: chat.value, type: type.value, direction: direction.value })
}
function reset() {
  query.value = ''; dateFrom.value = ''; dateTo.value = ''; chat.value = ''; type.value = ''; direction.value = ''; chatQuery.value = ''
  submit()
}
</script>

<template>
  <section class="feature-pane global-search" aria-labelledby="global-search-title">
    <div class="global-search__toolbar">
      <h2 id="global-search-title">Encontre uma mensagem no arquivo</h2>
      <p>Busque em todas as conversas, incluindo as arquivadas neste painel.</p>
      <form class="global-search__form" @submit.prevent="submit">
        <label class="global-query"><span>Texto ou legenda</span><div class="search-field"><AppIcon name="search" :size="20" /><input v-model="query" maxlength="200" type="search" placeholder="Buscar em todas as mensagens" /></div></label>
        <button class="button button--quiet mobile-filter-toggle" type="button" :aria-expanded="filtersOpen" aria-controls="global-search-filters" @click="filtersOpen = !filtersOpen"><AppIcon name="next" :size="16" :class="{ 'filters-chevron--open': filtersOpen }" />{{ filtersOpen ? 'Ocultar filtros' : 'Mostrar filtros' }}<span v-if="activeFilters" class="active-filter-count">{{ activeFilters }} {{ activeFilters === 1 ? 'ativo' : 'ativos' }}</span></button>
        <div id="global-search-filters" class="search-filters-grid" :class="{ 'search-filters-grid--expanded': filtersOpen }">
          <label><span>De</span><input v-model="dateFrom" type="date" :max="dateTo || undefined" /></label>
          <label><span>Até</span><input v-model="dateTo" type="date" :min="dateFrom || undefined" /></label>
          <label class="search-chat"><span>Conversa</span><input v-model="chatQuery" maxlength="200" type="search" placeholder="Encontrar nome ou número" aria-label="Encontrar conversa para filtrar" /><select v-model="chat" aria-label="Conversa da busca"><option value="">Todas as conversas</option><option v-for="conversation in options" :key="conversation.chat" :value="conversation.chat">{{ chatLabel(conversation) }}</option></select></label>
          <label><span>Tipo</span><select v-model="type" aria-label="Tipo"><option value="">Todos os tipos</option><option v-for="item in types" :key="item" :value="item">{{ mediaLabel(item) }}</option></select></label>
          <label><span>Direção</span><select v-model="direction" aria-label="Direção"><option value="">Recebidas e enviadas</option><option value="in">Recebidas</option><option value="out">Enviadas</option></select></label>
        </div>
        <div class="search-actions"><p v-if="validation" class="form-error" role="alert">{{ validation }}</p><span v-else-if="optionsBusy" class="loading-copy">Buscando conversas…</span><button class="button button--quiet" type="button" :disabled="busy" @click="reset">Limpar filtros</button><button class="button button--primary" type="submit" :disabled="busy"><AppIcon :name="busy ? 'loading' : 'search'" :class="{ spin: busy }" :size="18" />{{ busy ? 'Buscando…' : 'Buscar mensagens' }}</button></div>
      </form>
    </div>
    <div class="search-results" :aria-busy="busy">
      <div v-if="searched" class="search-results__count" role="status">{{ formatCount(page.total) }} {{ page.total === 1 ? 'mensagem encontrada' : 'mensagens encontradas' }}</div>
      <EmptyState v-if="!page.items.length" compact icon="search" :title="searched ? 'Nenhuma mensagem encontrada' : 'Sua busca começa aqui'" :description="searched ? 'Tente outras palavras ou ajuste os filtros.' : 'Escolha os filtros para encontrar mensagens preservadas.'" />
      <button v-for="message in page.items" :key="message.chat + ':' + message.id" class="search-result" @click="$emit('open', message)">
        <PhotoAvatar :chat="message.chat" :name="chatLabel(message.conversation || { chat: message.chat })" />
        <span class="search-result__content"><span class="search-result__heading"><strong>{{ chatLabel(message.conversation || { chat: message.chat }) }}</strong><time>{{ formatDate(message.timestamp, '') }}</time></span><span class="search-result__meta">{{ message.from_me ? 'Enviada' : 'Recebida' }} · {{ mediaLabel(message.type) }}<span v-if="message.conversation?.archived_local"> · Arquivada neste painel</span></span><span class="search-result__text">{{ message.text || mediaLabel(message.type) }}</span><span class="search-result__open">Abrir conversa <AppIcon name="arrow" :size="13" /></span></span>
      </button>
    </div>
    <PageControls :page="page.page" :pages="page.pages" :busy="busy" @change="$emit('page', $event)" />
    <ArchiveFooter />
  </section>
</template>
