<script setup>
// Module 2: the farmer enters soil and weather values, the server's model
// recommends a crop, and this page shows why that crop fits.
import {
  AlertTriangle,
  Check,
  CircleAlert,
  CloudSun,
  LocateFixed,
  MessagesSquare,
  Mountain,
  Sprout,
  Volume2,
  VolumeX,
} from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ConfidenceRing from '../../components/ConfidenceRing.vue'
import { cropMeta, loadCropMeta, recommendCrop } from '../../lib/api'
import { cropContext, setLastResult } from '../../lib/context'
import { useI18n } from '../../lib/i18n'
import { canSpeak, speak, speaking, stopSpeaking } from '../../lib/speech'
import { getWeather } from '../../lib/weather'

const { t, advisorCropName, lang } = useI18n()
const router = useRouter()

const SOIL = ['N', 'P', 'K', 'ph']
const CLIMATE = ['temperature', 'humidity', 'rainfall']
const WITH_PRESETS = ['N', 'P', 'K', 'rainfall'] // fields that offer Low / Medium / High
const STEP = { N: 1, P: 1, K: 1, ph: 0.1, temperature: 0.5, humidity: 1, rainfall: 1 }

const values = reactive({ N: '', P: '', K: '', ph: '', temperature: '', humidity: '', rainfall: '' })
const status = ref('idle') // idle | loading | done | error
const result = ref(null)
const errorField = ref('')
const errorCode = ref('')
const weatherNote = ref('')
const weatherBusy = ref(false)

onMounted(async () => {
  await loadCropMeta()
  fillDefaults()
})
watch(cropMeta, fillDefaults)

// Start every field at the middle value of the training data, so the sliders are not empty.
function fillDefaults() {
  if (!cropMeta.value) return
  for (const field of [...SOIL, ...CLIMATE]) {
    if (values[field] === '') values[field] = tidy(field, cropMeta.value.features[field].median)
  }
}

// Whole numbers where the slider moves in whole steps, one decimal otherwise.
function tidy(field, number) {
  const decimals = STEP[field] < 1 ? 1 : 0
  return Number(Number(number).toFixed(decimals))
}

const feature = (field) => cropMeta.value?.features[field]
const preset = (field, level) => {
  const value = feature(field)?.presets[level]
  return value === undefined ? undefined : tidy(field, value)
}
const isPreset = (field, level) => Number(values[field]) === preset(field, level)

async function useMyWeather() {
  weatherBusy.value = true
  weatherNote.value = ''
  try {
    const weather = await getWeather()
    values.temperature = Math.round(weather.temperature * 10) / 10
    values.humidity = Math.round(weather.humidity)
    weatherNote.value = t('crop.weatherFilled')
  } catch (error) {
    weatherNote.value = t(`weather.${error.message}`)
  } finally {
    weatherBusy.value = false
  }
}

async function submit() {
  errorField.value = ''
  errorCode.value = ''
  // Empty boxes are caught here; out-of-range numbers are caught by the server.
  const empty = [...SOIL, ...CLIMATE].find((field) => values[field] === '' || values[field] === null)
  if (empty) {
    errorField.value = empty
    return
  }
  status.value = 'loading'
  stopSpeaking()
  try {
    const [response] = await Promise.all([recommendCrop({ ...values }), new Promise((r) => setTimeout(r, 600))])
    result.value = response
    status.value = 'done'
    setLastResult(cropContext(response))
  } catch (error) {
    if (error.code === 'invalid_input') {
      status.value = result.value ? 'done' : 'idle'
      errorField.value = error.field || ''
      if (!error.field) errorCode.value = 'server_error'
    } else {
      status.value = 'error'
      errorCode.value = error.code || 'server_error'
    }
  }
}

const best = computed(() => result.value?.recommendation)
const tone = computed(() => (result.value?.low_confidence ? 'unsure' : 'good'))
const others = computed(() => (result.value?.alternatives || []).slice(1).filter((option) => option.confidence >= 0.01))
const threshold = computed(() => Math.round((result.value?.threshold ?? 0.7) * 100))
const outsideNames = computed(() => (result.value?.outside_training_range || []).map((field) => t(`crop.${field}`)).join(', '))

// Where a value sits on a feature's full scale, as a percentage (for the range bars).
function position(field, number) {
  const scale = feature(field)
  if (!scale) return 0
  return Math.min(100, Math.max(0, ((number - scale.min) / (scale.max - scale.min)) * 100))
}

function listen() {
  if (speaking.value) return stopSpeaking()
  const percent = Math.round(best.value.confidence * 100)
  speak([
    { text: `${t('crop.best')}: ${advisorCropName(best.value.crop)}. ${t('crop.confidence')} ${percent}%.`, lang: lang.value },
    result.value.low_confidence ? { text: t('crop.lowText', { threshold: threshold.value }), lang: lang.value } : {},
  ])
}

function askAssistant() {
  router.push({ name: 'assistant' })
}

onBeforeUnmount(stopSpeaking)
</script>

<template>
  <div>
    <header>
      <h1 class="font-display text-4xl font-bold text-fog sm:text-5xl">{{ t('crop.title') }}</h1>
      <p class="mt-2 max-w-2xl text-lg text-mist">{{ t('crop.subtitle') }}</p>
    </header>

    <div class="mt-8 grid items-start gap-6 xl:grid-cols-[1.05fr_1fr]">
      <!-- ================= The form ================= -->
      <form class="glass rounded-[2rem] p-6 sm:p-8" novalidate @submit.prevent="submit">
        <div v-for="group in [{ id: 'soil', icon: Mountain, fields: SOIL }, { id: 'climate', icon: CloudSun, fields: CLIMATE }]" :key="group.id" class="group-block">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <h2 class="flex items-center gap-3 font-display text-2xl font-bold text-fog">
              <span class="grid size-10 place-items-center rounded-xl bg-lime/12 text-lime"><component :is="group.icon" class="size-5" /></span>
              {{ t(`crop.${group.id}`) }}
            </h2>
            <button v-if="group.id === 'climate'" type="button" class="btn btn-ghost !min-h-11 !px-4 !text-sm" :disabled="weatherBusy" @click="useMyWeather">
              <LocateFixed class="size-4" :class="{ 'animate-pulse': weatherBusy }" /> {{ t('crop.useWeather') }}
            </button>
          </div>
          <p v-if="group.id === 'climate' && weatherNote" class="mt-3 text-sm text-mist" role="status">{{ weatherNote }}</p>

          <div class="mt-5 space-y-6">
            <div v-for="field in group.fields" :key="field">
              <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
                <label :for="`field-${field}`" class="text-lg font-semibold text-fog">{{ t(`crop.${field}`) }}</label>
                <div v-if="WITH_PRESETS.includes(field) && feature(field)" class="flex gap-1.5">
                  <button
                    v-for="level in ['low', 'medium', 'high']"
                    :key="level"
                    type="button"
                    class="chip"
                    :class="{ active: isPreset(field, level) }"
                    @click="values[field] = preset(field, level)"
                  >
                    {{ t(`crop.${level}`) }}
                  </button>
                </div>
              </div>
              <div class="mt-3 flex items-center gap-4">
                <input
                  v-if="feature(field)"
                  v-model.number="values[field]"
                  type="range"
                  class="slider flex-1"
                  :min="feature(field).min"
                  :max="feature(field).max"
                  :step="STEP[field]"
                  :aria-label="t(`crop.${field}`)"
                  tabindex="-1"
                />
                <input
                  :id="`field-${field}`"
                  v-model.number="values[field]"
                  type="number"
                  inputmode="decimal"
                  class="number"
                  :class="{ invalid: errorField === field }"
                  :step="STEP[field]"
                  :aria-invalid="errorField === field"
                  :data-testid="`input-${field}`"
                />
              </div>
              <p v-if="errorField === field" class="mt-2 flex items-center gap-2 text-sm font-medium text-rose" role="alert">
                <CircleAlert class="size-4" /> {{ t('crop.invalid') }}
              </p>
            </div>
          </div>
        </div>

        <p class="mt-7 rounded-2xl border border-dashed border-white/15 px-4 py-3 text-sm leading-relaxed text-mist">{{ t('crop.hint') }}</p>

        <button type="submit" class="btn btn-primary btn-lg mt-6 w-full" :disabled="status === 'loading' || !cropMeta" data-testid="crop-submit">
          <Sprout class="size-5" /> {{ status === 'loading' ? t('crop.working') : t('crop.submit') }}
        </button>
      </form>

      <!-- ================= The result ================= -->
      <div aria-live="polite">
        <div v-if="status === 'idle'" class="glass grid min-h-[26rem] place-items-center rounded-[2rem] p-8 text-center">
          <div>
            <span class="icon-tile amber animate-float mx-auto !size-20 !rounded-3xl"><Sprout class="size-9" /></span>
            <p class="mt-6 text-2xl font-semibold text-fog">{{ t('crop.waiting') }}</p>
            <p class="mt-1 text-mist">{{ t('crop.waitingText') }}</p>
          </div>
        </div>

        <div v-else-if="status === 'loading'" class="glass min-h-[26rem] space-y-5 rounded-[2rem] p-8">
          <div class="flex items-center gap-6">
            <div class="size-40 shrink-0 animate-pulse rounded-full bg-white/8" />
            <div class="flex-1 space-y-4">
              <div class="h-5 w-24 animate-pulse rounded bg-white/8" />
              <div class="h-10 w-2/3 animate-pulse rounded-lg bg-white/10" />
            </div>
          </div>
          <div class="h-40 animate-pulse rounded-2xl bg-white/6" />
        </div>

        <div v-else-if="status === 'error'" class="glass rounded-[2rem] border-rose/35 p-8 text-center">
          <span class="mx-auto grid size-16 place-items-center rounded-2xl bg-rose/15 text-rose"><CircleAlert class="size-8" /></span>
          <p class="mx-auto mt-5 max-w-md text-xl font-semibold text-fog">{{ t(`errors.${errorCode}`) }}</p>
        </div>

        <div v-else-if="result" class="space-y-5" data-testid="crop-result">
          <section class="animate-rise glass relative overflow-hidden rounded-[2rem] p-7 sm:p-8" :class="tone === 'good' ? 'border-lime/30' : 'border-amber/35'">
            <div class="glow -right-20 -top-24 size-72" :class="tone === 'good' ? 'bg-lime/20' : 'bg-amber/20'" />
            <div class="relative flex flex-col items-center gap-7 text-center sm:flex-row sm:text-left">
              <ConfidenceRing :value="best.confidence" :tone="tone" :label="t('crop.confidence')" />
              <div class="min-w-0">
                <div class="text-sm font-semibold uppercase tracking-wider text-dim">{{ t('crop.best') }}</div>
                <div class="font-display text-4xl font-extrabold leading-tight sm:text-5xl" :class="tone === 'good' ? 'text-lime' : 'text-amber'" data-testid="crop-name">
                  {{ advisorCropName(best.crop, true) }}
                </div>
                <div class="mt-5 flex flex-wrap justify-center gap-2 sm:justify-start">
                  <button v-if="canSpeak" type="button" class="btn btn-ghost !min-h-11 !px-4 !text-sm" @click="listen">
                    <VolumeX v-if="speaking" class="size-4" /><Volume2 v-else class="size-4" />
                    {{ speaking ? t('voice.stop') : t('voice.listen') }}
                  </button>
                  <button type="button" class="btn btn-ghost !min-h-11 !px-4 !text-sm" @click="askAssistant">
                    <MessagesSquare class="size-4" /> {{ t('voice.ask') }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <section
            v-if="result.low_confidence"
            class="animate-rise flex gap-4 rounded-3xl border border-amber/40 bg-amber/10 p-5 sm:p-6"
            role="alert"
            data-testid="crop-low-confidence"
          >
            <AlertTriangle class="mt-0.5 size-7 shrink-0 text-amber" />
            <div>
              <h2 class="text-lg font-bold text-amber">{{ t('crop.lowTitle') }}</h2>
              <p class="mt-1 leading-relaxed text-fog/90">{{ t('crop.lowText', { threshold }) }}</p>
              <p v-if="outsideNames" class="mt-2 font-medium text-fog">{{ t('crop.outsideRange', { fields: outsideNames }) }}</p>
            </div>
          </section>

          <!-- why: each value against the range this crop grows in -->
          <section class="animate-rise glass rounded-[2rem] p-6 sm:p-7" style="animation-delay: 120ms">
            <h2 class="font-display text-2xl font-bold text-fog">{{ t('crop.why') }}</h2>
            <p class="mt-1 text-mist">{{ t('crop.whyText') }}</p>
            <ul class="mt-5 space-y-5">
              <li v-for="reason in result.reasons" :key="reason.feature">
                <div class="flex items-center justify-between gap-3">
                  <span class="font-semibold text-fog">{{ t(`crop.${reason.feature}`) }}</span>
                  <span class="inline-flex items-center gap-1.5 text-sm font-semibold" :class="reason.fits ? 'text-lime' : 'text-amber'">
                    <Check v-if="reason.fits" class="size-4" :stroke-width="3" /><AlertTriangle v-else class="size-4" />
                    {{ reason.fits ? t('crop.fits') : t('crop.outside') }}
                  </span>
                </div>
                <div class="range">
                  <div class="range-band" :style="{ left: `${position(reason.feature, reason.low)}%`, right: `${100 - position(reason.feature, reason.high)}%` }" />
                  <div class="range-marker" :class="{ off: !reason.fits }" :style="{ left: `${position(reason.feature, reason.value)}%` }" />
                </div>
                <div class="mt-1.5 flex justify-between text-sm text-mist">
                  <span>{{ t('crop.yours') }}: <b class="text-fog">{{ reason.value }}</b></span>
                  <span>{{ t('crop.range') }}: {{ reason.low }} - {{ reason.high }}</span>
                </div>
              </li>
            </ul>
          </section>

          <section v-if="others.length" class="animate-rise glass rounded-3xl p-5 sm:p-6" style="animation-delay: 200ms">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-dim">{{ t('crop.others') }}</h2>
            <div class="mt-4 space-y-4">
              <div v-for="option in others" :key="option.crop">
                <div class="flex items-baseline justify-between gap-4">
                  <span class="font-medium text-fog">{{ advisorCropName(option.crop, true) }}</span>
                  <span class="font-display font-bold tabular-nums text-mist">{{ (option.confidence * 100).toFixed(1) }}%</span>
                </div>
                <div class="mt-2 h-2 overflow-hidden rounded-full bg-white/8">
                  <div class="h-full rounded-full bg-gradient-to-r from-leaf to-lime" :style="{ width: `${option.confidence * 100}%` }" />
                </div>
              </div>
            </div>
          </section>

          <p class="rounded-2xl border border-dashed border-white/15 px-5 py-4 text-sm leading-relaxed text-mist">{{ t('crop.disclaimer') }}</p>
          <p v-if="cropMeta?.metrics" class="px-1 text-sm text-dim">
            {{ t('crop.model') }}: {{ cropMeta.model }} · {{ t('crop.accuracy') }} {{ (cropMeta.metrics.test_accuracy * 100).toFixed(1) }}%
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.group-block + .group-block {
  margin-top: 2.25rem;
  padding-top: 2rem;
  border-top: 1px solid rgb(255 255 255 / 0.08);
}
.chip {
  min-height: 2.25rem;
  padding: 0 0.9rem;
  border-radius: 999px;
  border: 1px solid rgb(255 255 255 / 0.12);
  background: rgb(255 255 255 / 0.04);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-mist);
  transition:
    background 0.2s ease,
    color 0.2s ease,
    border-color 0.2s ease;
}
.chip:hover {
  color: var(--color-fog);
  border-color: rgb(255 255 255 / 0.3);
}
.chip.active {
  color: var(--color-ink-950);
  background: var(--color-lime);
  border-color: transparent;
}
.number {
  width: 6.5rem;
  min-height: 3.25rem;
  padding: 0 0.9rem;
  border-radius: 1rem;
  border: 1px solid rgb(255 255 255 / 0.14);
  background: rgb(5 13 8 / 0.6);
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 700;
  text-align: center;
  color: var(--color-fog);
  -moz-appearance: textfield;
  appearance: textfield;
}
.number::-webkit-outer-spin-button,
.number::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.number:focus {
  outline: 2px solid var(--color-lime);
  outline-offset: 2px;
}
.number.invalid {
  border-color: var(--color-rose);
}
.slider {
  height: 0.5rem;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.1);
  accent-color: var(--color-lime);
  cursor: pointer;
}

/* the crop's range (band) and the farmer's value (marker) on the feature's full scale */
.range {
  position: relative;
  height: 0.75rem;
  margin-top: 0.6rem;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.07);
}
.range-band {
  position: absolute;
  top: 0;
  bottom: 0;
  min-width: 6px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgb(47 191 113 / 0.55), rgb(185 245 81 / 0.55));
}
.range-marker {
  position: absolute;
  top: 50%;
  width: 1.15rem;
  height: 1.15rem;
  margin: -0.575rem 0 0 -0.575rem;
  border-radius: 50%;
  border: 3px solid var(--color-ink-950);
  background: var(--color-lime);
  box-shadow: 0 0 14px var(--color-lime);
}
.range-marker.off {
  background: var(--color-amber);
  box-shadow: 0 0 14px var(--color-amber);
}
</style>
