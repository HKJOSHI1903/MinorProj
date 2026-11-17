<script setup>
// A circular gauge that fills up to the model's confidence and counts the number up.
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({
  value: { type: Number, required: true }, // 0..1
  tone: { type: String, default: 'good' }, // good | bad | unsure
  label: { type: String, default: '' },
  size: { type: Number, default: 168 },
})

const RADIUS = 52
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

const shown = ref(0) // the animated value, 0..1
const colour = computed(() => ({ good: '#b9f551', bad: '#ff6b5e', unsure: '#ffb547' })[props.tone])
const dashOffset = computed(() => CIRCUMFERENCE * (1 - shown.value))

function animate(target) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    shown.value = target
    return
  }
  const from = shown.value
  const start = performance.now()
  const duration = 1100
  function step(now) {
    const k = Math.min((now - start) / duration, 1)
    const eased = 1 - Math.pow(1 - k, 4)
    shown.value = from + (target - from) * eased
    if (k < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

onMounted(() => animate(props.value))
watch(() => props.value, animate)
</script>

<template>
  <div class="relative shrink-0" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg viewBox="0 0 120 120" class="size-full -rotate-90" :style="{ filter: `drop-shadow(0 0 14px ${colour}66)` }">
      <circle cx="60" cy="60" :r="RADIUS" fill="none" stroke="rgb(255 255 255 / 0.08)" stroke-width="9" />
      <circle
        cx="60"
        cy="60"
        :r="RADIUS"
        fill="none"
        :stroke="colour"
        stroke-width="9"
        stroke-linecap="round"
        :stroke-dasharray="CIRCUMFERENCE"
        :stroke-dashoffset="dashOffset"
      />
    </svg>
    <div class="absolute inset-0 grid place-items-center text-center">
      <div>
        <div class="font-display text-4xl font-bold leading-none tabular-nums text-fog">
          {{ Math.round(shown * 100) }}<span class="text-xl text-mist">%</span>
        </div>
        <div v-if="label" class="mt-1 text-xs font-medium uppercase tracking-wider text-mist">{{ label }}</div>
      </div>
    </div>
  </div>
</template>
