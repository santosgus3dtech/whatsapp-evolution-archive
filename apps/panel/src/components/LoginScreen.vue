<script setup>
import { ref } from 'vue'
import AppIcon from './AppIcon.vue'
import BrandMark from './BrandMark.vue'
defineProps({ busy: Boolean, error: String })
const emit = defineEmits(['login'])
const username = ref('')
const password = ref('')
function submit() {
  const credentials = { username: username.value.trim(), password: password.value }
  password.value = ''
  emit('login', credentials)
}
</script>

<template>
  <main class="login-screen">
    <div class="login-brand"><BrandMark dark /><span>Whatsapp Evolution Manager</span></div>
    <section class="login-card" aria-labelledby="login-title">
      <div class="login-lock"><AppIcon name="lock" :size="27" /></div>
      <h1 id="login-title">Seu arquivo, em segurança.</h1>
      <p>Entre para acessar as mensagens preservadas no seu servidor.</p>
      <form class="login-form" @submit.prevent="submit">
        <label for="username">Usuário</label>
        <input id="username" v-model="username" name="username" autocomplete="username" required autofocus :disabled="busy" />
        <label for="password">Senha</label>
        <input id="password" v-model="password" name="password" type="password" autocomplete="current-password" required :disabled="busy" />
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button button--primary" type="submit" :disabled="busy">
          <AppIcon v-if="busy" name="loading" :size="19" class="spin" />
          {{ busy ? 'Entrando…' : 'Entrar no arquivo' }}
        </button>
      </form>
      <p class="login-private"><AppIcon name="shield" :size="16" /> Acesso privado</p>
    </section>
  </main>
</template>
