<script setup>
defineProps({ dark: { type: Boolean, default: true } })
const base = import.meta.env.BASE_URL
</script>

<template>
  <img class="brand-logo" :src="base + 'brand/logo-' + (dark ? 'dark' : 'light') + '.svg'" alt="Whatsapp Evolution Manager" width="192" />
</template>
