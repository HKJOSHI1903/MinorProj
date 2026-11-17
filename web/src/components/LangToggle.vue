<script setup>
import { useI18n } from '../lib/i18n'

const { lang, setLanguage } = useI18n()
const options = [
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'hi', label: 'हिं', name: 'हिन्दी' },
]
</script>

<template>
  <div
    class="relative inline-grid grid-cols-2 rounded-full border border-white/10 bg-white/5 p-1 text-sm font-semibold"
    role="group"
    aria-label="Language / भाषा"
  >
    <!-- the sliding highlight -->
    <span
      class="absolute inset-y-1 left-1 w-[calc(50%-0.25rem)] rounded-full bg-lime transition-transform duration-300 ease-[var(--ease-out-expo)]"
      :class="lang === 'hi' ? 'translate-x-full' : 'translate-x-0'"
    />
    <button
      v-for="option in options"
      :key="option.code"
      type="button"
      class="relative z-10 min-w-12 rounded-full px-3 py-1.5 transition-colors duration-200"
      :class="lang === option.code ? 'text-ink-950' : 'text-mist hover:text-fog'"
      :aria-pressed="lang === option.code"
      :title="option.name"
      @click="setLanguage(option.code)"
    >
      {{ option.label }}
    </button>
  </div>
</template>
