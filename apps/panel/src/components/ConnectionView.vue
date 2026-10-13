<script setup>
import AppIcon from './AppIcon.vue'
import ArchiveFooter from './ArchiveFooter.vue'
import { formatBytes, formatDate } from '../lib/format'
defineProps({ status: Object, connected: Boolean, label: String, busy: Boolean })
defineEmits(['connect'])
</script>

<template>
  <section class="feature-pane connection-view" aria-labelledby="connection-title">
    <div class="feature-content">
      <div class="feature-heading"><div><h2 id="connection-title">Seu WhatsApp, vinculado</h2><p>O número continua disponível no seu celular.</p></div><span class="connection-status" :class="{ 'connection-status--online': connected }"><span class="status-dot" />{{ label }}</span></div>
      <div class="connection-body"><div class="connection-illustration"><AppIcon name="phone" :size="56" /></div><h3>{{ connected ? 'Seu arquivo está recebendo mensagens.' : 'Pronto para começar o seu arquivo.' }}</h3><p>{{ connected ? 'As novas mensagens são preservadas enquanto a conexão permanece ativa.' : 'Vincule este servidor como um dispositivo do WhatsApp para receber e preservar as mensagens.' }}</p><button class="button button--primary" :disabled="busy" @click="$emit('connect')"><AppIcon :name="connected ? 'qr' : 'message'" :size="20" />{{ connected ? 'Ver conexão' : 'Vincular WhatsApp' }}</button></div>
      <dl class="connection-details"><div><dt>Arquivo</dt><dd>{{ status?.instance || 'Aguardando configuração' }}</dd></div><div><dt>Início da captura</dt><dd>{{ formatDate(status?.capture_started) }}</dd></div><div><dt>Espaço disponível no servidor</dt><dd>{{ formatBytes(status?.storage?.free_bytes) }}</dd></div></dl>
      <p class="history-explanation">A visualização e as marcações deste painel são locais. Elas não enviam mensagens e não alteram os indicadores de leitura no WhatsApp.</p>
    </div>
    <ArchiveFooter />
  </section>
</template>
