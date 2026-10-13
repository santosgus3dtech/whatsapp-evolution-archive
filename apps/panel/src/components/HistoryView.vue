<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import ArchiveFooter from './ArchiveFooter.vue'
import { formatCount, formatDate } from '../lib/format'
const props = defineProps({ status: Object, busy: Boolean, connected: Boolean })
defineEmits(['sync'])
const canResume = computed(() => props.status?.sync?.incomplete && ['interrupted', 'error', 'failed', 'blocked', 'limited'].includes(props.status?.sync?.state))
const stateLabels = { idle: 'Aguardando importação', queued: 'Importação na fila', running: 'Importando histórico', syncing: 'Importando histórico', complete: 'Importação concluída', completed: 'Importação concluída', done: 'Importação concluída', failed: 'Importação interrompida', error: 'Importação interrompida', interrupted: 'Importação interrompida', blocked: 'Importação pausada', limited: 'Limite desta importação atingido' }
</script>

<template>
  <section class="feature-pane history-view" aria-labelledby="history-title">
    <div class="feature-content">
      <div class="feature-heading"><div><h2 id="history-title">O que foi preservado</h2><p>Consulte a cobertura real do seu arquivo.</p></div><button class="button button--primary" :disabled="busy || !status?.configured || !connected" @click="$emit('sync')"><AppIcon :name="busy ? 'loading' : 'refresh'" :class="{ spin: busy }" :size="19" />{{ busy ? 'Importando…' : canResume ? 'Retomar importação' : 'Importar histórico disponível' }}</button></div>
      <dl class="coverage-list">
        <div><dt>Mensagens preservadas</dt><dd>{{ formatCount(status?.counts?.messages) }}</dd></div>
        <div><dt>Conversas no arquivo</dt><dd>{{ formatCount(status?.counts?.conversations) }}</dd></div>
        <div><dt>Primeira mensagem disponível</dt><dd>{{ formatDate(status?.coverage?.first_message_at) }}</dd></div>
        <div><dt>Última mensagem disponível</dt><dd>{{ formatDate(status?.coverage?.last_message_at) }}</dd></div>
      </dl>
      <div class="sync-status" role="status"><AppIcon :name="busy ? 'loading' : 'history'" :class="{ spin: busy }" :size="25" /><div><h3>{{ stateLabels[status?.sync?.state] || 'Aguardando importação' }}</h3><p v-if="status?.sync?.processed || busy">{{ formatCount(status?.sync?.processed) }} mensagens processadas<span v-if="status?.sync?.pages"> · página {{ status.sync.current_page || 1 }} de {{ status.sync.pages }}</span></p><p v-else-if="['complete', 'completed', 'done'].includes(status?.sync?.state)">A consulta ao banco da Evolution foi concluída. A cobertura anterior continua não verificada.</p><p v-else>Vincule seu WhatsApp para disponibilizar o histórico sincronizado.</p></div></div>
      <p v-if="status?.sync?.incomplete && !busy && (status?.sync?.started_at || ['limited', 'interrupted', 'error', 'failed', 'blocked'].includes(status?.sync?.state)) && status?.sync?.state !== 'idle'" class="coverage-note"><AppIcon name="info" :size="18" />A importação ficou incompleta. Você pode tentar novamente.</p>
      <p v-if="canResume && status?.sync?.next_page" class="checkpoint-note">A importação pode continuar da página {{ status.sync.next_page }}<span v-if="status.sync.resume_count"> · {{ status.sync.resume_count }} retomada{{ status.sync.resume_count === 1 ? '' : 's' }}</span>.</p>
      <p v-if="status?.sync?.error" class="form-error" role="alert">Não foi possível concluir a importação. Verifique a conexão e tente novamente.</p>
      <p class="history-explanation">O arquivo reúne as mensagens que o dispositivo vinculado recebeu. Conversas antigas podem ficar apenas no celular, mesmo após a sincronização.</p>
    </div>
    <ArchiveFooter />
  </section>
</template>
