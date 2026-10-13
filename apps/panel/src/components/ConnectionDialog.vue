<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
const props = defineProps({ open: Boolean, image: String, busy: Boolean, error: String, expired: Boolean, connected: Boolean })
const emit = defineEmits(['close', 'retry'])
const dialog = ref(null)
let previousFocus
watch(() => props.open, async open => {
  await nextTick()
  if (open) {
    previousFocus = document.activeElement
    if (!dialog.value.open) dialog.value.showModal()
  } else {
    dialog.value?.close()
    previousFocus?.focus?.()
  }
})
onBeforeUnmount(() => dialog.value?.close())
</script>

<template>
  <dialog ref="dialog" class="connection-dialog" aria-labelledby="qr-title" @cancel.prevent="emit('close')" @click="event => event.target === dialog && emit('close')">
    <button class="icon-button dialog-close" aria-label="Fechar vínculo" @click="emit('close')"><AppIcon name="close" /></button>
    <template v-if="connected"><div class="connected-symbol"><AppIcon name="check" :size="38" /></div><h2 id="qr-title">WhatsApp vinculado</h2><p>As mensagens recebidas ficarão disponíveis no seu arquivo.</p><button class="button button--primary" @click="emit('close')">Ir para o arquivo</button></template>
    <template v-else><h2 id="qr-title">Vincule seu WhatsApp</h2><p>No celular, abra <strong>Dispositivos conectados</strong>, toque em <strong>Conectar um dispositivo</strong> e leia o QR code.</p><div class="qr-frame"><img v-if="image && !expired" :src="image" alt="QR code para vincular o WhatsApp" /><div v-else class="qr-placeholder"><AppIcon :name="busy ? 'loading' : expired ? 'refresh' : 'qr'" :class="{ spin: busy }" :size="48" /><span>{{ busy ? 'Preparando QR code…' : expired ? 'O QR code expirou' : 'Aguardando QR code' }}</span></div></div><p v-if="error" class="form-error" role="alert">{{ error }}</p><p class="qr-note">{{ expired ? 'Gere um novo código para continuar.' : 'O código é atualizado enquanto esta janela estiver aberta.' }}</p><button v-if="error || expired || (!image && !busy)" class="button button--primary" :disabled="busy" @click="emit('retry')"><AppIcon name="refresh" :size="18" />Gerar novo QR code</button><p class="qr-private"><AppIcon name="lock" :size="15" />Seu número continua no celular.</p></template>
  </dialog>
</template>
