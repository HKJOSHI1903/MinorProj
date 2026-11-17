<script setup>
import { watchEffect } from 'vue'
import { useI18n } from './lib/i18n'

const { lang } = useI18n()

// Keeps <html lang="..."> right, which also switches the font for Hindi.
watchEffect(() => {
  document.documentElement.lang = lang.value
})
</script>

<template>
  <RouterView />
</template>
