import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { request, queryString, apiUrl } from '../lib/api'
import { connectionState } from '../lib/format'

const emptyPage = () => ({ items: [], total: 0, page: 1, page_size: 50, pages: 0 })

export function useArchive() {
  const session = ref(null)
  const booting = ref(true)
  const loginBusy = ref(false)
  const loginError = ref('')
  const error = ref('')
  const notice = ref('')
  const tab = ref('conversations')
  const status = ref(null)
  const conversationQuery = ref('')
  const messageQuery = ref('')
  const favoritesOnly = ref(false)
  const labelFilter = ref('')
  const preferencesBusy = ref(false)
  const chatOptions = ref([])
  const allLabels = ref([])
  const optionsBusy = ref(false)
  const searchPage = ref(emptyPage())
  const searchBusy = ref(false)
  const searched = ref(false)
  const searchFilters = ref({})
  const selectedChat = ref(null)
  const selectedConversation = ref(null)
  const conversationPage = ref(emptyPage())
  const messagePage = ref(emptyPage())
  const conversationsBusy = ref(false)
  const messagesBusy = ref(false)
  const seenBusy = ref(false)
  const syncStarting = ref(false)
  const qrOpen = ref(false)
  const qrBusy = ref(false)
  const qrImage = ref('')
  const qrError = ref('')
  const qrExpired = ref(false)
  let eventSource
  let refreshTimer
  let queryTimer
  let messageQueryTimer
  let qrTimer
  let qrStartedAt = 0
  let conversationRequestId = 0
  let messageRequestId = 0
  let searchRequestId = 0
  let optionsRequestId = 0
  let checkingSession = false
  let lastSessionCheckAt = 0
  let disposed = false

  const authenticated = computed(() => session.value?.authenticated === true)
  const connected = computed(() => connectionState(status.value?.connection) === 'open')
  const connectionLabel = computed(() => {
    const state = connectionState(status.value?.connection)
    if (state === 'open') return 'WhatsApp conectado'
    if (state === 'connecting') return 'Vínculo em andamento'
    if (!status.value?.counts?.messages) return 'Aguardando vínculo'
    if (status.value?.configured && state === 'unknown') return 'Conexão indisponível'
    if (status.value?.capture_started) return 'WhatsApp desconectado'
    return 'Aguardando vínculo'
  })
  const activeConversation = computed(() => conversationPage.value.items.find(item => item.chat === selectedChat.value) || selectedConversation.value)
  const availableLabels = computed(() => [...new Set([
    ...conversationPage.value.items.flatMap(item => item.labels || []),
    ...chatOptions.value.flatMap(item => item.labels || []),
    ...allLabels.value,
    ...(labelFilter.value ? [labelFilter.value] : []),
  ])].sort((a, b) => a.localeCompare(b, 'pt-BR')))
  const syncBusy = computed(() => syncStarting.value || ['queued', 'running', 'syncing', 'starting'].includes(status.value?.sync?.state))

  async function call(path, options = {}) {
    try {
      return await request(path, { ...options, csrf: options.method && options.method !== 'GET' ? session.value?.csrf : undefined })
    } catch (failure) {
      if (failure.status === 401) expireSession()
      throw failure
    }
  }

  function closeEvents() {
    eventSource?.close()
    eventSource = undefined
    clearTimeout(refreshTimer)
  }

  function expireSession() {
    closeEvents()
    stopQrPolling()
    qrOpen.value = false
    session.value = { authenticated: false }
    status.value = null
    selectedChat.value = null
    selectedConversation.value = null
    conversationPage.value = emptyPage()
    messagePage.value = emptyPage()
    searchPage.value = emptyPage()
    chatOptions.value = []
    allLabels.value = []
    searched.value = false
    loginError.value = 'Sua sessão terminou. Entre novamente para continuar.'
  }

  async function loadSession() {
    session.value = await request('/api/session')
    return session.value
  }

  async function login(credentials) {
    loginBusy.value = true
    loginError.value = ''
    try {
      await request('/api/login', { method: 'POST', body: credentials })
      await loadSession()
      if (authenticated.value) await startArchive()
    } catch (failure) {
      loginError.value = failure.status === 401 ? 'Usuário ou senha incorretos.' : failure.message
    } finally {
      loginBusy.value = false
    }
  }

  async function logout() {
    try {
      await call('/api/logout', { method: 'POST' })
      expireSession()
      loginError.value = ''
    } catch (failure) {
      error.value = failure.message
    }
  }

  async function refreshStatus() {
    const result = await call('/api/status')
    if (authenticated.value && !disposed) status.value = result
    if (connected.value && qrOpen.value) stopQrPolling()
    return result
  }

  async function loadConversations(page = conversationPage.value.page || 1) {
    const sequence = ++conversationRequestId
    conversationsBusy.value = true
    try {
      const params = {
        page, page_size: 50, q: conversationQuery.value.trim(), unseen_only: tab.value === 'new' ? 'true' : undefined,
        favorites_only: favoritesOnly.value ? 'true' : undefined, label: labelFilter.value,
        archived: tab.value === 'archived' ? 'archived' : 'active',
      }
      const result = await call('/api/conversations?' + queryString(params))
      if (sequence === conversationRequestId && authenticated.value) conversationPage.value = { ...emptyPage(), ...result }
    } catch (failure) {
      if (sequence === conversationRequestId) error.value = failure.message
    } finally {
      if (sequence === conversationRequestId) conversationsBusy.value = false
    }
  }

  async function loadMessages(page = messagePage.value.page || 1) {
    if (!selectedChat.value) return
    const sequence = ++messageRequestId
    const chat = selectedChat.value
    messagesBusy.value = true
    try {
      const result = await call('/api/messages?' + queryString({ chat, q: messageQuery.value.trim(), page, page_size: 50 }))
      if (sequence === messageRequestId && authenticated.value && selectedChat.value === chat) messagePage.value = { ...emptyPage(), ...result }
    } catch (failure) {
      if (sequence === messageRequestId) error.value = failure.message
    } finally {
      if (sequence === messageRequestId) messagesBusy.value = false
    }
  }

  function selectChat(chat) {
    selectedChat.value = chat
    selectedConversation.value = conversationPage.value.items.find(item => item.chat === chat) || { chat }
    messageQuery.value = ''
    messagePage.value = emptyPage()
    loadMessages(1)
  }

  async function loadChatOptions(query = '') {
    const sequence = ++optionsRequestId
    optionsBusy.value = true
    try {
      const result = await call('/api/conversations?' + queryString({ archived: 'all', page: 1, page_size: 200, q: query }))
      if (sequence === optionsRequestId && authenticated.value) chatOptions.value = result.items || []
    } catch (failure) { error.value = failure.message }
    finally { if (sequence === optionsRequestId) optionsBusy.value = false }
  }

  async function loadLabels() {
    try {
      const result = await call('/api/conversations/labels')
      if (authenticated.value) allLabels.value = result.items || []
    } catch (failure) { error.value = failure.message }
  }

  async function searchMessages(filters = searchFilters.value, page = 1) {
    const sequence = ++searchRequestId
    searchFilters.value = { ...filters }
    searchBusy.value = true
    try {
      const result = await call('/api/search?' + queryString({ ...filters, page, page_size: 50 }))
      if (sequence === searchRequestId && authenticated.value) {
        searchPage.value = { ...emptyPage(), ...result }
        searched.value = true
      }
    } catch (failure) { if (sequence === searchRequestId) error.value = failure.message }
    finally { if (sequence === searchRequestId) searchBusy.value = false }
  }

  function changeSearchPage(page) { return searchMessages(searchFilters.value, page) }

  async function openSearchResult(message) {
    tab.value = message.conversation?.archived_local ? 'archived' : 'conversations'
    await nextTick()
    favoritesOnly.value = false
    labelFilter.value = ''
    conversationQuery.value = ''
    selectedConversation.value = { chat: message.chat, ...message.conversation }
    selectedChat.value = message.chat
    messageQuery.value = searchFilters.value.q || ''
    messagePage.value = emptyPage()
    await loadMessages(1)
  }

  async function updatePreferences(preferences) {
    if (!selectedChat.value || preferencesBusy.value) return
    const chat = selectedChat.value
    preferencesBusy.value = true
    try {
      const response = await call('/api/conversations/preferences', { method: 'POST', body: { chat, ...preferences } })
      if (selectedChat.value === chat) selectedConversation.value = { ...activeConversation.value, ...response }
      conversationPage.value.items = conversationPage.value.items.map(item => item.chat === chat ? { ...item, ...response } : item)
      if (preferences.archived_local !== undefined) {
        notice.value = preferences.archived_local ? 'Conversa arquivada neste painel. O WhatsApp não foi alterado.' : 'Conversa restaurada neste painel. O WhatsApp não foi alterado.'
      } else if (preferences.labels) notice.value = 'Etiquetas salvas neste painel.'
      await Promise.all([loadConversations(), loadChatOptions(), loadLabels()])
    } catch (failure) { error.value = failure.message }
    finally { preferencesBusy.value = false }
  }

  async function markSeen() {
    if (!selectedChat.value) return
    seenBusy.value = true
    try {
      await call('/api/seen', { method: 'POST', body: { chat: selectedChat.value } })
      if (selectedConversation.value) selectedConversation.value = { ...selectedConversation.value, unseen: 0 }
      await Promise.all([refreshStatus(), loadConversations(), loadMessages()])
      notice.value = 'Conversa marcada como vista neste arquivo.'
    } catch (failure) {
      error.value = failure.message
    } finally {
      seenBusy.value = false
    }
  }

  async function refreshArchive() {
    if (!authenticated.value || disposed) return
    try {
      await Promise.all([
        refreshStatus(), loadConversations(), selectedChat.value ? loadMessages() : Promise.resolve(),
        tab.value === 'search' && searched.value ? searchMessages(searchFilters.value, searchPage.value.page) : Promise.resolve(),
      ])
    } catch (failure) {
      error.value = failure.message
    }
  }

  function openEvents() {
    closeEvents()
    const cursor = Number(status.value?.event_cursor) || 0
    eventSource = new EventSource(apiUrl('/api/events?cursor=' + encodeURIComponent(cursor)), { withCredentials: true })
    eventSource.addEventListener('archive', event => {
      try {
        const update = JSON.parse(event.data)
        if (update.counts && status.value) status.value.counts = { ...status.value.counts, ...update.counts }
        if (update.sync && status.value) status.value.sync = update.sync
      } catch { /* A malformed event is reconciled by a server refresh. */ }
      clearTimeout(refreshTimer)
      refreshTimer = setTimeout(refreshArchive, 250)
    })
    eventSource.onerror = async () => {
      if (checkingSession || !authenticated.value || disposed || Date.now() - lastSessionCheckAt < 30_000) return
      checkingSession = true
      lastSessionCheckAt = Date.now()
      try {
        const current = await request('/api/session')
        if (!current?.authenticated) expireSession()
        else session.value = current
      } catch { /* EventSource resumes after a transient network failure. */ }
      finally { checkingSession = false }
    }
  }

  async function startArchive() {
    error.value = ''
    await refreshArchive()
    if (authenticated.value) await Promise.all([loadChatOptions(), loadLabels()])
    if (authenticated.value) openEvents()
  }

  async function startHistorySync() {
    syncStarting.value = true
    error.value = ''
    try {
      const response = await call('/api/history/sync', { method: 'POST' })
      if (response?.sync && status.value) status.value.sync = response.sync
      await refreshStatus()
    } catch (failure) {
      error.value = failure.message
    } finally {
      syncStarting.value = false
    }
  }

  function stopQrPolling() {
    clearInterval(qrTimer)
    qrTimer = undefined
  }

  function normaliseQr(response) {
    const qr = response?.qrcode || response?.data?.qrcode || response
    const value = qr?.base64
    if (typeof value !== 'string') return ''
    if (/^data:image\/(png|jpeg|webp);base64,[a-zA-Z0-9+/=\s]+$/.test(value)) return value
    if (/^[a-zA-Z0-9+/=\s]+$/.test(value)) return 'data:image/png;base64,' + value
    return ''
  }

  async function refreshQr() {
    if (!qrOpen.value || qrBusy.value || connected.value) return
    qrBusy.value = true
    qrError.value = ''
    try {
      const state = await call('/api/instance/connection')
      if (status.value) status.value.connection = state
      if (connectionState(state) === 'open') {
        stopQrPolling()
        await refreshArchive()
        return
      }
      const response = await call('/api/instance/connect', { method: 'POST' })
      const image = normaliseQr(response)
      if (image) qrImage.value = image
      await refreshStatus()
    } catch (failure) {
      qrError.value = failure.message
    } finally {
      qrBusy.value = false
    }
  }

  async function bindWhatsApp() {
    stopQrPolling()
    qrOpen.value = true
    qrBusy.value = true
    qrExpired.value = false
    qrError.value = ''
    qrImage.value = ''
    try {
      await call('/api/instance/setup', { method: 'POST' })
      const response = await call('/api/instance/connect', { method: 'POST' })
      qrImage.value = normaliseQr(response)
      await refreshStatus()
      if (qrOpen.value && !connected.value) {
        qrStartedAt = Date.now()
        qrTimer = setInterval(() => {
          if (Date.now() - qrStartedAt >= 5 * 60 * 1000) {
            stopQrPolling()
            qrExpired.value = true
            qrImage.value = ''
          } else refreshQr()
        }, 30_000)
      }
    } catch (failure) {
      qrError.value = failure.message
    } finally {
      qrBusy.value = false
    }
  }

  function closeQr() {
    qrOpen.value = false
    stopQrPolling()
    qrImage.value = ''
  }

  watch(tab, () => {
    conversationPage.value = emptyPage()
    selectedChat.value = null
    selectedConversation.value = null
    messagePage.value = emptyPage()
    messageQuery.value = ''
    if (authenticated.value && ['conversations', 'new', 'archived'].includes(tab.value)) loadConversations(1)
    if (tab.value === 'search') {
      searchPage.value = emptyPage(); searched.value = false; searchFilters.value = {}
      if (authenticated.value) loadChatOptions()
    }
  })
  watch(conversationQuery, () => {
    clearTimeout(queryTimer)
    queryTimer = setTimeout(() => authenticated.value && loadConversations(1), 250)
  })
  watch(messageQuery, () => {
    clearTimeout(messageQueryTimer)
    messageQueryTimer = setTimeout(() => authenticated.value && loadMessages(1), 250)
  })
  watch([favoritesOnly, labelFilter], () => { if (authenticated.value) loadConversations(1) })
  watch(connected, value => { if (value) stopQrPolling() })

  onMounted(async () => {
    try {
      await loadSession()
      if (authenticated.value) await startArchive()
    } catch (failure) {
      loginError.value = failure.message
    } finally {
      booting.value = false
    }
  })
  onBeforeUnmount(() => {
    disposed = true
    closeEvents()
    stopQrPolling()
    clearTimeout(queryTimer)
    clearTimeout(messageQueryTimer)
  })

  return {
    session, booting, authenticated, loginBusy, loginError, error, notice, tab, status,
    conversationQuery, messageQuery, selectedChat, conversationPage, messagePage,
    conversationsBusy, messagesBusy, seenBusy, syncBusy, connected, connectionLabel, activeConversation,
    qrOpen, qrBusy, qrImage, qrError, qrExpired, login, logout, loadConversations, loadMessages,
    selectChat, markSeen, refreshArchive, startHistorySync, bindWhatsApp, refreshQr, closeQr,
    favoritesOnly, labelFilter, availableLabels, preferencesBusy, updatePreferences,
    searchPage, searchBusy, searched, chatOptions, optionsBusy, searchMessages, changeSearchPage, openSearchResult, loadChatOptions,
  }
}
