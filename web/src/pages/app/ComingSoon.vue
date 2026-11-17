<script setup>
// Shown for the two modules that are still being built. It says so plainly
// instead of showing a form that does nothing.
import { ArrowRight, Check, MessagesSquare, Sprout } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from '../../lib/i18n'

const props = defineProps({ module: { type: String, required: true } }) // 'crop' | 'assistant'
const { t } = useI18n()

const look = computed(() =>
  props.module === 'crop' ? { icon: Sprout, tile: 'amber', glow: 'bg-amber/20' } : { icon: MessagesSquare, tile: 'sky', glow: 'bg-sky/20' },
)
</script>

<template>
  <div class="grid min-h-[70dvh] place-items-center">
    <section v-tilt="3" class="tilt glass relative w-full max-w-2xl overflow-hidden rounded-[2.5rem] p-8 text-center sm:p-12">
      <div class="glow left-1/2 top-[-45%] size-96 -translate-x-1/2" :class="look.glow" />
      <div class="lift relative">
        <span class="icon-tile animate-float mx-auto !size-20 !rounded-3xl" :class="look.tile">
          <component :is="look.icon" class="size-9" />
        </span>
        <div class="mt-7"><span class="badge badge-soon !px-4 !py-1.5 !text-sm">{{ t('soon.badge') }}</span></div>
        <h1 class="font-display mt-5 text-4xl font-bold text-fog sm:text-5xl">{{ t(`soon.${module}.title`) }}</h1>
        <p class="mx-auto mt-4 max-w-lg text-lg leading-relaxed text-mist">{{ t(`soon.${module}.text`) }}</p>

        <ul class="mx-auto mt-8 max-w-md space-y-3 text-left">
          <li v-for="point in ['p1', 'p2', 'p3']" :key="point" class="flex items-center gap-3 rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
            <span class="grid size-7 shrink-0 place-items-center rounded-lg bg-lime/15 text-lime"><Check class="size-4" :stroke-width="3" /></span>
            <span class="font-medium text-fog">{{ t(`soon.${module}.${point}`) }}</span>
          </li>
        </ul>

        <RouterLink :to="{ name: 'disease' }" class="btn btn-primary btn-lg mt-9">
          {{ t('soon.back') }} <ArrowRight class="size-5" />
        </RouterLink>
      </div>
    </section>
  </div>
</template>
