<script setup>
import {
  ArrowRight,
  ArrowUpRight,
  Camera,
  Check,
  ClipboardCheck,
  Cpu,
  FlaskConical,
  Languages,
  Menu,
  MessagesSquare,
  ScanLine,
  ShieldCheck,
  Sprout,
  X,
} from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppLogo from '../components/AppLogo.vue'
import LangToggle from '../components/LangToggle.vue'
import LeafHero from '../components/LeafHero.vue'
import { loadMeta, meta } from '../lib/api'
import { useI18n } from '../lib/i18n'

const { t, cropName } = useI18n()

const CROPS = [
  'Apple', 'Blueberry', 'Cherry (including sour)', 'Corn (maize)', 'Grape', 'Orange', 'Peach',
  'Pepper, bell', 'Potato', 'Raspberry', 'Soybean', 'Squash', 'Strawberry', 'Tomato',
]

const scrolled = ref(false)
const menuOpen = ref(false)
const onScroll = () => (scrolled.value = window.scrollY > 24)

onMounted(() => {
  loadMeta() // real model numbers; the page still works if the server is off
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))

const percent = (value, digits = 1) => (typeof value === 'number' ? `${(value * 100).toFixed(digits)}%` : null)
const metrics = computed(() => meta.value?.metrics || null)

// The headline numbers. They are read from the server, never typed in here.
const stats = computed(() => [
  { value: percent(metrics.value?.test_accuracy), label: t('stats.accuracy') },
  { value: meta.value ? String(meta.value.classes.length) : null, label: t('stats.conditions') },
  { value: meta.value ? String(meta.value.crops.length) : null, label: t('stats.crops') },
  { value: metrics.value ? metrics.value.images.train.toLocaleString('en-IN') : null, label: t('stats.photos') },
])

const scores = computed(() =>
  [
    { key: 'accuracy', value: metrics.value?.test_accuracy },
    { key: 'precision', value: metrics.value?.macro_precision },
    { key: 'recall', value: metrics.value?.macro_recall },
    { key: 'f1', value: metrics.value?.macro_f1 },
  ].filter((score) => typeof score.value === 'number'),
)

const navLinks = [
  { hash: '#features', key: 'nav.features' },
  { hash: '#how', key: 'nav.how' },
  { hash: '#crops', key: 'nav.crops' },
  { hash: '#model', key: 'nav.model' },
]
</script>

<template>
  <div class="relative">
    <!-- ================= Navigation ================= -->
    <header class="fixed inset-x-0 top-0 z-50 px-4 pt-3 sm:px-6">
      <nav
        class="mx-auto flex h-16 max-w-7xl items-center justify-between rounded-2xl px-4 transition-all duration-500 sm:px-5"
        :class="scrolled || menuOpen ? 'glass bg-ink-900/70' : 'border border-transparent'"
      >
        <RouterLink :to="{ name: 'home' }" aria-label="Kisan Sahayak"><AppLogo /></RouterLink>

        <div class="hidden items-center gap-8 text-[0.95rem] font-medium text-mist lg:flex">
          <a v-for="link in navLinks" :key="link.hash" :href="link.hash" class="transition-colors hover:text-fog">
            {{ t(link.key) }}
          </a>
        </div>

        <div class="flex items-center gap-2 sm:gap-3">
          <LangToggle />
          <RouterLink :to="{ name: 'overview' }" class="btn btn-primary hidden !min-h-11 !px-5 sm:inline-flex">
            {{ t('nav.open') }} <ArrowRight class="size-4" />
          </RouterLink>
          <button
            type="button"
            class="grid size-11 place-items-center rounded-full border border-white/10 bg-white/5 lg:hidden"
            :aria-expanded="menuOpen"
            aria-label="Menu"
            @click="menuOpen = !menuOpen"
          >
            <X v-if="menuOpen" class="size-5" /><Menu v-else class="size-5" />
          </button>
        </div>
      </nav>

      <!-- phone menu -->
      <div v-if="menuOpen" class="glass mx-auto mt-2 max-w-7xl rounded-2xl bg-ink-900/85 p-3 lg:hidden">
        <a
          v-for="link in navLinks"
          :key="link.hash"
          :href="link.hash"
          class="block rounded-xl px-4 py-3 text-lg font-medium text-fog hover:bg-white/5"
          @click="menuOpen = false"
        >
          {{ t(link.key) }}
        </a>
        <RouterLink :to="{ name: 'overview' }" class="btn btn-primary mt-2 w-full">
          {{ t('nav.open') }} <ArrowRight class="size-4" />
        </RouterLink>
      </div>
    </header>

    <main>
      <!-- ================= Hero ================= -->
      <section class="relative overflow-hidden">
        <div class="backdrop">
          <div class="glow -top-40 right-[-10%] size-[620px] bg-leaf/40" />
          <div class="glow left-[-12%] top-[30%] size-[480px] bg-lime/20" style="animation-delay: -6s" />
          <div class="glow bottom-[-30%] right-[20%] size-[520px] bg-amber/10" style="animation-delay: -11s" />
        </div>

        <div
          class="relative mx-auto grid max-w-7xl items-center gap-6 px-5 pb-10 pt-32 sm:px-8 lg:min-h-[100dvh] lg:grid-cols-[1.15fr_1fr] lg:gap-4 lg:pb-24 lg:pt-28"
        >
          <div class="relative z-10">
            <div class="animate-fade-up badge badge-live !px-4 !py-1.5 !text-[0.82rem]">
              <span class="dot" /> {{ t('hero.eyebrow') }}
            </div>
            <h1
              class="animate-fade-up font-display mt-6 text-[2.7rem] font-extrabold leading-[1.04] text-fog sm:text-6xl lg:text-[3.5rem] xl:text-[4.1rem]"
              style="animation-delay: 80ms"
            >
              {{ t('hero.title1') }}<br />
              <span class="text-gradient">{{ t('hero.title2') }}</span>
            </h1>
            <p class="animate-fade-up mt-6 max-w-xl text-lg leading-relaxed text-mist sm:text-xl" style="animation-delay: 160ms">
              {{ t('hero.text') }}
            </p>
            <div class="animate-fade-up mt-9 flex flex-col gap-3 sm:flex-row" style="animation-delay: 240ms">
              <RouterLink :to="{ name: 'disease' }" class="btn btn-primary btn-lg">
                <ScanLine class="size-5" /> {{ t('hero.primary') }}
              </RouterLink>
              <a href="#how" class="btn btn-ghost btn-lg">{{ t('hero.secondary') }}</a>
            </div>
          </div>

          <!-- the 3D leaf with floating status chips -->
          <div class="relative h-[420px] sm:h-[520px] lg:h-[640px]">
            <div
              class="absolute left-1/2 top-1/2 size-[78%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-leaf/15 blur-3xl"
            />
            <LeafHero />

            <div class="glass animate-float absolute left-0 top-[12%] flex items-center gap-3 rounded-2xl px-4 py-3 sm:left-[4%]">
              <span class="grid size-9 place-items-center rounded-xl bg-lime/15 text-lime"><ScanLine class="size-5" /></span>
              <span class="text-sm font-semibold text-fog">{{ t('hero.chipScan') }}</span>
              <span class="dot text-lime" />
            </div>
            <div
              class="glass animate-float absolute right-0 top-[44%] flex items-center gap-3 rounded-2xl px-4 py-3 sm:right-[2%]"
              style="animation-delay: -2s"
            >
              <span class="size-3 rounded-full bg-amber shadow-[0_0_14px_var(--color-amber)]" />
              <span class="text-sm font-semibold text-fog">{{ t('hero.chipSpot') }}</span>
            </div>
            <div
              class="glass animate-float absolute bottom-[1%] left-0 flex items-center gap-3 rounded-2xl px-4 py-3"
              style="animation-delay: -4s"
            >
              <span class="grid size-9 place-items-center rounded-xl bg-lime text-ink-950"><Check class="size-5" :stroke-width="3" /></span>
              <span class="text-sm font-semibold text-fog">{{ t('hero.chipPlan') }}</span>
            </div>
          </div>
        </div>

        <!-- real numbers from the last training run -->
        <div class="relative mx-auto max-w-7xl px-5 pb-20 sm:px-8">
          <div v-reveal class="glass grid grid-cols-2 divide-white/10 rounded-3xl lg:grid-cols-4 lg:divide-x">
            <div v-for="stat in stats" :key="stat.label" class="p-6 sm:p-8">
              <div v-if="stat.value" class="font-display text-4xl font-bold text-fog sm:text-5xl">{{ stat.value }}</div>
              <div v-else class="h-10 w-24 animate-pulse rounded-lg bg-white/10 sm:h-12" />
              <div class="mt-2 text-sm leading-snug text-mist sm:text-base">{{ stat.label }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= Features ================= -->
      <section id="features" class="relative mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
        <div v-reveal class="max-w-2xl">
          <div class="kicker">{{ t('features.kicker') }}</div>
          <h2 class="font-display mt-4 text-4xl font-bold leading-tight text-fog sm:text-5xl">{{ t('features.title') }}</h2>
        </div>

        <div class="mt-12 grid gap-5 lg:grid-cols-6">
          <!-- disease detection: the big card -->
          <article v-reveal v-tilt="5" class="tilt glass overflow-hidden rounded-[2rem] p-7 sm:p-9 lg:col-span-4">
            <div class="grid items-center gap-8 md:grid-cols-[1.1fr_1fr]">
              <div class="lift-sm">
                <div class="flex items-center gap-3">
                  <span class="icon-tile"><ScanLine class="size-6" /></span>
                  <span class="badge badge-live"><span class="dot" />{{ t('features.live') }}</span>
                </div>
                <h3 class="font-display mt-6 text-3xl font-bold text-fog">{{ t('features.disease.title') }}</h3>
                <p class="mt-3 text-lg leading-relaxed text-mist">{{ t('features.disease.text') }}</p>
                <RouterLink :to="{ name: 'disease' }" class="mt-6 inline-flex items-center gap-2 font-semibold text-lime hover:gap-3 transition-all">
                  {{ t('hero.primary') }} <ArrowUpRight class="size-5" />
                </RouterLink>
              </div>
              <!-- a small illustration of the scanner -->
              <div class="lift relative mx-auto aspect-square w-full max-w-[280px]">
                <div class="absolute inset-0 rounded-[1.75rem] border border-white/10 bg-ink-800/80" />
                <div class="absolute inset-4 overflow-hidden rounded-2xl bg-gradient-to-br from-ink-700 to-ink-900">
                  <Sprout class="absolute left-1/2 top-1/2 size-28 -translate-x-1/2 -translate-y-1/2 text-leaf/80" :stroke-width="1" />
                  <div class="scan-line" />
                </div>
                <span v-for="corner in ['tl', 'tr', 'bl', 'br']" :key="corner" class="corner" :class="corner" />
              </div>
            </div>
          </article>

          <article v-reveal="80" v-tilt class="tilt glass rounded-[2rem] p-7 sm:p-8 lg:col-span-2">
            <span class="icon-tile lift"><FlaskConical class="size-6" /></span>
            <h3 class="font-display lift-sm mt-6 text-2xl font-bold text-fog">{{ t('features.advice.title') }}</h3>
            <p class="lift-sm mt-3 leading-relaxed text-mist">{{ t('features.advice.text') }}</p>
          </article>

          <article v-reveal v-tilt class="tilt glass rounded-[2rem] p-7 sm:p-8 lg:col-span-3">
            <span class="icon-tile amber lift"><ShieldCheck class="size-6" /></span>
            <h3 class="font-display lift-sm mt-6 text-2xl font-bold text-fog">{{ t('features.safety.title') }}</h3>
            <p class="lift-sm mt-3 leading-relaxed text-mist">{{ t('features.safety.text') }}</p>
          </article>

          <article v-reveal="80" v-tilt class="tilt glass rounded-[2rem] p-7 sm:p-8 lg:col-span-3">
            <span class="icon-tile sky lift"><Languages class="size-6" /></span>
            <h3 class="font-display lift-sm mt-6 text-2xl font-bold text-fog">{{ t('features.language.title') }}</h3>
            <p class="lift-sm mt-3 leading-relaxed text-mist">{{ t('features.language.text') }}</p>
          </article>

          <article v-reveal v-tilt class="tilt glass rounded-[2rem] p-7 sm:p-8 lg:col-span-3">
            <div class="lift flex items-center gap-3">
              <span class="icon-tile amber"><Sprout class="size-6" /></span>
              <span class="badge badge-live"><span class="dot" />{{ t('features.live') }}</span>
            </div>
            <h3 class="font-display lift-sm mt-6 text-2xl font-bold text-fog">{{ t('features.crop.title') }}</h3>
            <p class="lift-sm mt-3 leading-relaxed text-mist">{{ t('features.crop.text') }}</p>
            <RouterLink :to="{ name: 'crop' }" class="lift-sm mt-5 inline-flex items-center gap-2 font-semibold text-lime transition-all hover:gap-3">
              {{ t('app.crop') }} <ArrowUpRight class="size-5" />
            </RouterLink>
          </article>

          <article v-reveal="80" v-tilt class="tilt glass rounded-[2rem] p-7 sm:p-8 lg:col-span-3">
            <div class="lift flex items-center gap-3">
              <span class="icon-tile sky"><MessagesSquare class="size-6" /></span>
              <span class="badge badge-live"><span class="dot" />{{ t('features.live') }}</span>
            </div>
            <h3 class="font-display lift-sm mt-6 text-2xl font-bold text-fog">{{ t('features.assistant.title') }}</h3>
            <p class="lift-sm mt-3 leading-relaxed text-mist">{{ t('features.assistant.text') }}</p>
            <RouterLink :to="{ name: 'assistant' }" class="lift-sm mt-5 inline-flex items-center gap-2 font-semibold text-lime transition-all hover:gap-3">
              {{ t('app.assistant') }} <ArrowUpRight class="size-5" />
            </RouterLink>
          </article>
        </div>
      </section>

      <!-- ================= How it works ================= -->
      <section id="how" class="relative border-y border-white/5 bg-ink-900/60">
        <div class="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-28">
          <div v-reveal class="max-w-2xl">
            <div class="kicker">{{ t('how.kicker') }}</div>
            <h2 class="font-display mt-4 text-4xl font-bold leading-tight text-fog sm:text-5xl">{{ t('how.title') }}</h2>
          </div>

          <ol class="relative mt-14 grid gap-10 lg:grid-cols-3 lg:gap-8">
            <div class="absolute left-0 right-0 top-9 hidden h-px bg-gradient-to-r from-lime/0 via-lime/40 to-lime/0 lg:block" />
            <li
              v-for="(step, index) in [
                { key: 's1', icon: Camera },
                { key: 's2', icon: Cpu },
                { key: 's3', icon: ClipboardCheck },
              ]"
              :key="step.key"
              v-reveal="index * 120"
              class="relative"
            >
              <div class="flex items-center gap-4">
                <span
                  class="relative grid size-[4.5rem] shrink-0 place-items-center rounded-3xl border border-lime/30 bg-ink-950 text-lime shadow-[0_0_40px_-10px_var(--color-lime)]"
                >
                  <component :is="step.icon" class="size-8" :stroke-width="1.6" />
                </span>
                <span class="font-display text-6xl font-extrabold text-white/10">0{{ index + 1 }}</span>
              </div>
              <h3 class="font-display mt-6 text-2xl font-bold text-fog">{{ t(`how.${step.key}.title`) }}</h3>
              <p class="mt-3 max-w-sm text-lg leading-relaxed text-mist">{{ t(`how.${step.key}.text`) }}</p>
            </li>
          </ol>
        </div>
      </section>

      <!-- ================= Crops ================= -->
      <section id="crops" class="relative overflow-hidden py-20 lg:py-28">
        <div v-reveal class="mx-auto max-w-7xl px-5 sm:px-8">
          <div class="kicker">{{ t('crops.kicker') }}</div>
          <h2 class="font-display mt-4 text-4xl font-bold leading-tight text-fog sm:text-5xl">{{ t('crops.title') }}</h2>
        </div>
        <!-- the list is repeated once so the loop has no visible seam -->
        <div class="marquee mt-12" aria-hidden="true">
          <div class="marquee-track">
            <span v-for="(crop, index) in [...CROPS, ...CROPS]" :key="index" class="marquee-item">
              <Sprout class="size-6 text-lime" /> {{ cropName(crop) }}
            </span>
          </div>
        </div>
        <p class="sr-only">{{ CROPS.map((crop) => cropName(crop)).join(', ') }}</p>
      </section>

      <!-- ================= The model ================= -->
      <section id="model" class="relative mx-auto max-w-7xl px-5 pb-20 sm:px-8 lg:pb-28">
        <div class="grid items-start gap-10 lg:grid-cols-2 lg:gap-16">
          <div v-reveal>
            <div class="kicker">{{ t('model.kicker') }}</div>
            <h2 class="font-display mt-4 text-4xl font-bold leading-tight text-fog sm:text-5xl">{{ t('model.title') }}</h2>
            <p class="mt-5 max-w-lg text-lg leading-relaxed text-mist">{{ t('model.text') }}</p>

            <dl class="mt-9 divide-y divide-white/10 border-y border-white/10">
              <div v-for="row in ['arch', 'data', 'split', 'threshold']" :key="row" class="grid gap-1 py-4 sm:grid-cols-[11rem_1fr]">
                <dt class="text-sm font-medium uppercase tracking-wider text-dim">{{ t(`model.${row}`) }}</dt>
                <dd class="text-lg font-medium text-fog">{{ t(`model.${row}Value`) }}</dd>
              </div>
            </dl>
          </div>

          <div v-reveal="120" v-tilt="4" class="tilt glass rounded-[2rem] p-7 sm:p-9">
            <template v-if="scores.length">
              <div v-for="score in scores" :key="score.key" class="lift-sm py-4 first:pt-0 last:pb-0">
                <div class="flex items-baseline justify-between">
                  <span class="text-base font-medium text-mist">{{ t(`model.${score.key}`) }}</span>
                  <span class="font-display text-3xl font-bold tabular-nums text-fog">{{ percent(score.value) }}</span>
                </div>
                <div class="mt-3 h-2.5 overflow-hidden rounded-full bg-white/8">
                  <div
                    class="h-full rounded-full bg-gradient-to-r from-leaf to-lime shadow-[0_0_18px_var(--color-lime)]"
                    :style="{ width: `${score.value * 100}%` }"
                  />
                </div>
              </div>
              <p v-if="metrics" class="lift-sm mt-6 border-t border-white/10 pt-5 text-sm text-dim">
                {{ metrics.images.test.toLocaleString('en-IN') }} test · {{ metrics.images.train.toLocaleString('en-IN') }} train ·
                {{ metrics.classes }} classes
              </p>
            </template>
            <p v-else class="py-10 text-center text-mist">{{ t('model.offline') }}</p>
          </div>
        </div>
      </section>

      <!-- ================= Call to action ================= -->
      <section class="mx-auto max-w-7xl px-5 pb-20 sm:px-8">
        <div
          v-reveal
          class="relative overflow-hidden rounded-[2.5rem] border border-lime/20 bg-gradient-to-br from-ink-700 via-ink-800 to-ink-900 px-7 py-16 text-center sm:px-12 sm:py-24"
        >
          <div class="glow left-1/2 top-[-60%] size-[560px] -translate-x-1/2 bg-lime/25" />
          <h2 class="font-display relative text-4xl font-extrabold leading-tight text-fog sm:text-6xl">{{ t('cta.title') }}</h2>
          <p class="relative mx-auto mt-4 max-w-md text-lg text-mist">{{ t('cta.text') }}</p>
          <RouterLink :to="{ name: 'overview' }" class="btn btn-primary btn-lg relative mt-9">
            {{ t('cta.button') }} <ArrowRight class="size-5" />
          </RouterLink>
        </div>
      </section>
    </main>

    <footer class="border-t border-white/5">
      <div class="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-10 sm:px-8 md:flex-row md:items-center md:justify-between">
        <AppLogo />
        <p class="max-w-xl text-sm leading-relaxed text-dim">{{ t('footer.note') }}</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* scanner illustration in the disease card */
.scan-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 28%;
  background: linear-gradient(180deg, transparent, rgb(185 245 81 / 0.28));
  border-bottom: 2px solid var(--color-lime);
  box-shadow: 0 8px 24px -4px var(--color-lime);
  animation: scan-sweep 2.6s cubic-bezier(0.5, 0, 0.5, 1) infinite alternate;
}
.corner {
  position: absolute;
  width: 26px;
  height: 26px;
  border: 3px solid var(--color-lime);
}
.corner.tl { top: 0; left: 0; border-right: 0; border-bottom: 0; border-top-left-radius: 1.75rem; }
.corner.tr { top: 0; right: 0; border-left: 0; border-bottom: 0; border-top-right-radius: 1.75rem; }
.corner.bl { bottom: 0; left: 0; border-right: 0; border-top: 0; border-bottom-left-radius: 1.75rem; }
.corner.br { bottom: 0; right: 0; border-left: 0; border-top: 0; border-bottom-right-radius: 1.75rem; }

/* crop names scrolling sideways */
.marquee {
  overflow: hidden;
  mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
}
.marquee-track {
  display: flex;
  width: max-content;
  animation: marquee 48s linear infinite;
}
.marquee:hover .marquee-track {
  animation-play-state: paused;
}
.marquee-item {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  margin-right: 1rem; /* a margin, not a flex gap, so the two halves are exactly equal */
  padding: 1rem 1.75rem;
  border-radius: 999px;
  border: 1px solid rgb(255 255 255 / 0.1);
  background: rgb(255 255 255 / 0.04);
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--color-fog);
}
</style>
