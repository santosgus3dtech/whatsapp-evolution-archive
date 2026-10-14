<script setup>
import { computed, ref } from 'vue'
import { useArchive } from './composables/useArchive'
import AppIcon from './components/AppIcon.vue'
import AppSidebar from './components/AppSidebar.vue'
import LoginScreen from './components/LoginScreen.vue'
import ConversationList from './components/ConversationList.vue'
import MessagePane from './components/MessagePane.vue'
import HistoryView from './components/HistoryView.vue'
import ConnectionView from './components/ConnectionView.vue'
import ConnectionDialog from './components/ConnectionDialog.vue'
import GlobalSearch from './components/GlobalSearch.vue'

const archive = useArchive()
const {
  booting, authenticated, loginBusy, loginError, error, notice, tab, status,
  conversationQuery, messageQuery, selectedChat, conversationPage, messagePage,
  conversationsBusy, messagesBusy, seenBusy, syncBusy, connected, connectionLabel, activeConversation,
  qrOpen, qrBusy, qrImage, qrError, qrExpired,
  favoritesOnly, labelFilter, availableLabels, preferencesBusy,
  searchPage, searchBusy, searched, chatOptions, optionsBusy,
} = archive
const menuOpen = ref(false)
const titles = { conversations: 'Conversas', new: 'Novas mensagens', search: 'Busca global', archived: 'Arquivadas', history: 'Histórico', connection: 'Conexão' }
const subtitle = computed(() => tab.value === 'new' ? 'Mensagens ainda não vistas neste arquivo.' : tab.value === 'archived' ? 'Conversas arquivadas neste painel.' : 'Mensagens preservadas no seu servidor.')
const showConversations = computed(() => ['conversations', 'new', 'archived'].includes(tab.value))
function navigate(next) {
  tab.value = next
  menuOpen.value = false
  notice.value = ''
}
</script>

<template>
  <div v-if="booting" class="boot-screen" role="status"><AppIcon name="loading" class="spin" :size="27" /><span>Abrindo seu arquivo…</span></div>
  <LoginScreen v-else-if="!authenticated" :busy="loginBusy" :error="loginError" @login="archive.login" />
  <div v-else class="app-shell">
    <a class="skip-link" href="#main-content">Ir para o conteúdo</a>
    <AppSidebar :active="tab" :unseen="status?.counts?.unseen || 0" :open="menuOpen" @navigate="navigate" @logout="archive.logout" @close="menuOpen = false" />
    <main id="main-content" class="main-area" aria-label="WhatsNexo">
      <header class="page-header">
        <button class="icon-button mobile-menu" aria-label="Abrir navegação" :aria-expanded="menuOpen" @click="menuOpen = !menuOpen"><AppIcon name="menu" /></button>
        <div class="page-header__title"><h1>{{ titles[tab] }}</h1><p>{{ subtitle }}</p></div>
        <span class="connection-status" :class="{ 'connection-status--online': connected }"><span class="status-dot" />{{ connectionLabel }}</span>
      </header>
      <div v-if="!connected" class="connection-banner">
        <div><AppIcon name="info" :size="23" /><p>Vincule seu WhatsApp para iniciar o arquivo.</p></div>
        <button class="button button--primary" :disabled="qrBusy" @click="archive.bindWhatsApp"><AppIcon name="message" :size="21" />Vincular WhatsApp</button>
      </div>
      <div v-if="status?.storage?.write_blocked" class="feedback feedback--error" role="alert"><AppIcon name="alert" :size="20" /><p>A gravação está pausada por falta de espaço no servidor.</p></div>
      <div v-if="error" class="feedback feedback--error" role="alert"><AppIcon name="alert" :size="20" /><p>{{ error }}</p><button class="icon-button" aria-label="Dispensar aviso" @click="error = ''"><AppIcon name="close" :size="18" /></button></div>
      <div v-if="notice" class="feedback feedback--success" role="status"><AppIcon name="check" :size="20" /><p>{{ notice }}</p><button class="icon-button" aria-label="Fechar confirmação" @click="notice = ''"><AppIcon name="close" :size="18" /></button></div>
      <div v-if="showConversations" class="archive-workspace" :class="{ 'archive-workspace--chat': selectedChat }">
        <ConversationList :page="conversationPage" v-model:query="conversationQuery" :selected-chat="selectedChat" :busy="conversationsBusy" :new-only="tab === 'new'" :archived="tab === 'archived'" v-model:favorites-only="favoritesOnly" v-model:label="labelFilter" :labels="availableLabels" @select="archive.selectChat" @page="archive.loadConversations" />
        <MessagePane :chat="selectedChat" :conversation="activeConversation" :page="messagePage" v-model:query="messageQuery" :busy="messagesBusy" :seen-busy="seenBusy" :preferences-busy="preferencesBusy" @preferences="archive.updatePreferences" @seen="archive.markSeen" @page="archive.loadMessages" @back="selectedChat = null" />
      </div>
      <GlobalSearch v-else-if="tab === 'search'" :page="searchPage" :busy="searchBusy" :searched="searched" :chat-options="chatOptions" :options-busy="optionsBusy" @search="archive.searchMessages" @page="archive.changeSearchPage" @open="archive.openSearchResult" @chat-query="archive.loadChatOptions" />
      <HistoryView v-else-if="tab === 'history'" :status="status" :busy="syncBusy" :connected="connected" @sync="archive.startHistorySync" />
      <ConnectionView v-else :status="status" :connected="connected" :label="connectionLabel" :busy="qrBusy" @connect="archive.bindWhatsApp" />
    </main>
    <ConnectionDialog :open="qrOpen" :image="qrImage" :busy="qrBusy" :error="qrError" :expired="qrExpired" :connected="connected" @close="archive.closeQr" @retry="archive.bindWhatsApp" />
  </div>
</template>
