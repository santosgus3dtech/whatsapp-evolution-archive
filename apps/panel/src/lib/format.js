const locale = 'pt-BR'

export function dateValue(value) {
  if (!value) return null
  const date = typeof value === 'number'
    ? new Date(value < 1e12 ? value * 1000 : value)
    : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value, fallback = 'Ainda sem registros') {
  const date = dateValue(value)
  return date ? new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(date) : fallback
}

export function formatTime(value) {
  const date = dateValue(value)
  return date ? new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(date) : ''
}

export function formatDay(value) {
  const date = dateValue(value)
  return date ? new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long', year: 'numeric' }).format(date) : ''
}

export function formatCount(value = 0) {
  return new Intl.NumberFormat(locale).format(Number(value) || 0)
}

export function formatBytes(value) {
  if (value === null || value === undefined) return 'Indisponível'
  const bytes = Number(value)
  if (!Number.isFinite(bytes)) return 'Indisponível'
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(bytes / 1024 ** 3) + ' GB'
}

export function chatLabel(conversation) {
  return conversation?.name || conversation?.push_name || conversation?.chat?.replace(/@(s\.whatsapp\.net|g\.us|lid)$/, '') || 'Conversa'
}

export function mediaLabel(type) {
  const labels = {
    text: 'Texto', image: 'Imagem', video: 'Vídeo', audio: 'Áudio', document: 'Documento',
    sticker: 'Figurinha', reaction: 'Reação', button: 'Resposta de botão', list: 'Resposta de lista',
    poll: 'Enquete', location: 'Localização', contact: 'Contato', contacts: 'Contatos', system: 'Atualização',
    imageMessage: 'Imagem', videoMessage: 'Vídeo', audioMessage: 'Áudio',
    documentMessage: 'Documento', stickerMessage: 'Figurinha',
    contactMessage: 'Contato', contactsArrayMessage: 'Contatos',
    locationMessage: 'Localização', liveLocationMessage: 'Localização',
    pollCreationMessage: 'Enquete', pollCreationMessageV3: 'Enquete',
    reactionMessage: 'Reação', unknown: 'Mensagem sem texto',
  }
  return labels[type] || 'Mensagem sem texto'
}

export function connectionState(connection) {
  if (typeof connection === 'string') return connection
  return connection?.state || connection?.status || 'close'
}
