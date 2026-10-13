<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import EmptyState from './EmptyState.vue'
import ArchiveFooter from './ArchiveFooter.vue'
import PageControls from './PageControls.vue'
import PhotoAvatar from './PhotoAvatar.vue'
import ConversationTools from './ConversationTools.vue'
import { chatLabel, dateValue, formatCount, formatTime, formatDay, mediaLabel } from '../lib/format'
const props = defineProps({ chat: String, conversation: Object, page: Object, query: String, busy: Boolean, seenBusy: Boolean, preferencesBusy: Boolean })
defineEmits(['update:query', 'seen', 'page', 'back', 'preferences'])
const messages = computed(() => [...props.page.items].sort((a, b) => (dateValue(a.timestamp)?.getTime() || 0) - (dateValue(b.timestamp)?.getTime() || 0)))
function startsDay(message, index) {
  return index === 0 || formatDay(message.timestamp) !== formatDay(messages.value[index - 1].timestamp)
}
</script>

<template>
  <section class="message-pane" :class="{ 'message-pane--selected': chat }" aria-label="Mensagens arquivadas" :aria-busy="busy">
    <template v-if="chat">
      <header class="message-pane__header">
        <button class="icon-button message-back" aria-label="Voltar às conversas" @click="$emit('back')"><AppIcon name="previous" /></button>
        <PhotoAvatar :chat="chat" :name="chatLabel(conversation || { chat })" />
        <div class="message-pane__identity"><h2>{{ chatLabel(conversation || { chat }) }}</h2><p>{{ formatCount(page.total) }} {{ page.total === 1 ? 'mensagem' : 'mensagens' }} {{ query ? (page.total === 1 ? 'encontrada' : 'encontradas') : 'no arquivo' }}</p></div>
        <button class="button button--quiet seen-button" :disabled="seenBusy || !(conversation?.unseen > 0)" @click="$emit('seen')"><AppIcon name="seen" :size="18" /><span>{{ seenBusy ? 'Marcando…' : 'Marcar como vista' }}</span></button>
      </header>
      <ConversationTools :conversation="conversation" :busy="preferencesBusy" @update="$emit('preferences', $event)" />
      <div class="message-search"><div class="search-field"><AppIcon name="search" :size="18" /><input :value="query" type="search" placeholder="Buscar nas mensagens" aria-label="Buscar nas mensagens desta conversa" @input="$emit('update:query', $event.target.value)" /></div><span v-if="busy" class="loading-copy">Carregando…</span></div>
      <div class="message-pane__messages">
        <EmptyState v-if="!messages.length" compact title="Nenhuma mensagem encontrada" :description="query ? 'Tente uma palavra diferente.' : 'As mensagens preservadas aparecerão aqui.'" />
        <template v-for="(message, index) in messages" :key="message.id">
          <p v-if="startsDay(message, index)" class="message-day">{{ formatDay(message.timestamp) }}</p>
          <article class="message-bubble" :class="{ 'message-bubble--outgoing': message.from_me, 'message-bubble--deleted': message.deleted }" :aria-label="message.from_me ? 'Mensagem enviada' : 'Mensagem recebida'">
            <p v-if="message.participant && !message.from_me" class="message-participant">{{ message.participant.replace(/@.*$/, '') }}</p>
            <p v-if="message.text" class="message-text">{{ message.text }}</p>
            <p v-else class="message-media"><AppIcon name="message" :size="16" />{{ mediaLabel(message.type) }}<span>Arquivo de mídia ainda não disponível.</span></p>
            <footer class="message-metadata"><span v-if="message.deleted">Apagada no WhatsApp</span><span v-else-if="message.edited">Editada</span><span v-if="message.historical">Histórico</span><time>{{ formatTime(message.timestamp) }}</time><AppIcon v-if="message.from_me" name="check" :size="14" /></footer>
          </article>
        </template>
      </div>
      <div class="message-pane__pagination"><span>Visualização local · sem alterar a leitura no WhatsApp</span><PageControls :page="page.page" :pages="page.pages" :busy="busy" @change="$emit('page', $event)" /></div>
    </template>
    <EmptyState v-else title="Selecione uma conversa" description="O histórico recebido ficará disponível aqui." />
    <ArchiveFooter />
  </section>
</template>
