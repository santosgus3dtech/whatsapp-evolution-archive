<script setup>
import { ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
const props = defineProps({ conversation: Object, busy: Boolean })
const emit = defineEmits(['update'])
const editing = ref(false)
const labelText = ref('')
const labelError = ref('')
watch(() => props.conversation?.chat, () => { editing.value = false; labelError.value = '' })
function editLabels() {
  labelText.value = (props.conversation?.labels || []).join(', ')
  labelError.value = ''
  editing.value = !editing.value
}
function saveLabels() {
  const labels = [...new Set(labelText.value.split(',').map(label => label.trim()).filter(Boolean))]
  if (labels.length > 20 || labels.some(label => label.length > 64)) {
    labelError.value = 'Use até 20 etiquetas, com no máximo 64 caracteres cada.'
    return
  }
  emit('update', { labels })
  editing.value = false
}
</script>

<template>
  <div class="conversation-tools">
    <button class="tool-button" :class="{ 'tool-button--favorite': conversation?.favorite }" :disabled="busy" :aria-pressed="Boolean(conversation?.favorite)" @click="$emit('update', { favorite: !conversation?.favorite })"><AppIcon name="star" :size="17" /><span>{{ conversation?.favorite ? 'Favorita' : 'Favoritar' }}</span></button>
    <button class="tool-button" :disabled="busy" :aria-expanded="editing" @click="editLabels"><AppIcon name="tag" :size="17" /><span>Etiquetas</span></button>
    <button class="tool-button" :disabled="busy" @click="$emit('update', { archived_local: !conversation?.archived_local })"><AppIcon :name="conversation?.archived_local ? 'restore' : 'archive'" :size="17" /><span>{{ conversation?.archived_local ? 'Restaurar no painel' : 'Arquivar no painel' }}</span></button>
    <span v-if="conversation?.archived_local" class="local-archive-note">Arquivada neste painel</span>
    <span v-if="!editing && conversation?.labels?.length" class="conversation-labels"><span v-for="label in conversation.labels" :key="label" :title="label">{{ label }}</span></span>
  </div>
  <form v-if="editing" class="labels-editor" @submit.prevent="saveLabels">
    <label for="conversation-labels">Etiquetas separadas por vírgula</label>
    <div><input id="conversation-labels" v-model="labelText" maxlength="1318" placeholder="Ex.: Família, Trabalho" /><button class="button button--primary" type="submit" :disabled="busy">Salvar</button><button class="icon-button" type="button" aria-label="Cancelar edição de etiquetas" @click="editing = false"><AppIcon name="close" :size="18" /></button></div>
    <p v-if="labelError" class="form-error" role="alert">{{ labelError }}</p>
    <small>As etiquetas e o arquivamento pertencem a este painel.</small>
  </form>
</template>
