<script setup>
import { useI18n } from '../lib/i18n'

defineProps({ compact: Boolean })
const { t } = useI18n()
</script>

<template>
  <span class="inline-flex items-center gap-3">
    <span
      class="grid size-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-lime-soft via-lime to-[#86cf1f] shadow-[inset_0_1px_0_rgb(255_255_255/0.7),0_10px_24px_-8px_rgb(185_245_81/0.6)]"
    >
      <svg viewBox="0 0 64 64" class="size-7" aria-hidden="true">
        <path
          d="M46 17C28 17 17 27 17 40c0 3 1 6 2 8 2-10 9-18 20-23-9 7-15 15-17 26 2 1 3 1 5 1 13 0 21-11 21-27 0-3-1-6-2-8z"
          fill="#07110b"
        />
      </svg>
    </span>
    <span v-if="!compact" class="font-display whitespace-nowrap text-lg font-bold tracking-tight text-fog sm:text-xl">{{ t('brand') }}</span>
  </span>
</template>
