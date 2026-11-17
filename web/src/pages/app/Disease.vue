<script setup>
// Module 1: the farmer adds a leaf photo, the server's model names the disease,
// and this page shows the result with the treatment advice.
import {
  AlertTriangle,
  Camera,
  CircleAlert,
  FlaskConical,
  ImagePlus,
  Leaf,
  RotateCcw,
  ScanLine,
  ShieldCheck,
  Sprout,
  Sun,
  Square,
  X,
} from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import ConfidenceRing from '../../components/ConfidenceRing.vue'
import { predictDisease } from '../../lib/api'
import { addScan, makeThumbnail } from '../../lib/history'
import { useI18n } from '../../lib/i18n'

const { t, cropName } = useI18n()

const MAX_BYTES = 10 * 1024 * 1024

const status = ref('idle') // idle | loading | done | error
const previewUrl = ref('')
const result = ref(null)
const errorCode = ref('')
const dragging = ref(false)
const activeTab = ref('organic')
const fileInput = ref(null)

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function analyse(file) {
  if (!file) return
  result.value = null
  errorCode.value = ''

  // Checks that can be done before anything is uploaded.
  if (!file.type.startsWith('image/')) return fail('not_image_type')
  if (file.size > MAX_BYTES) return fail('file_too_large')

  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(file)
  status.value = 'loading'

  try {
    // The short wait lets the scan animation be seen even when the model answers instantly.
    const [response] = await Promise.all([predictDisease(file), wait(900)])
    result.value = response
    activeTab.value = 'organic'
    status.value = 'done'
    addScan(response, await makeThumbnail(file))
  } catch (error) {
    fail(error.code || 'server_error')
  }
}

function fail(code) {
  errorCode.value = code
  status.value = 'error'
}

function reset() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  result.value = null
  errorCode.value = ''
  status.value = 'idle'
}

function onFileChosen(event) {
  analyse(event.target.files?.[0])
  event.target.value = '' // so choosing the same file again still triggers a scan
}

function onDrop(event) {
  dragging.value = false
  analyse(event.dataTransfer?.files?.[0])
}

// ----- what the result panel shows -----
const prediction = computed(() => result.value?.prediction)
const advice = computed(() => result.value?.advice)
const tone = computed(() => {
  if (!result.value) return 'good'
  if (result.value.low_confidence) return 'unsure'
  return prediction.value.healthy ? 'good' : 'bad'
})
const toneClasses = computed(
  () =>
    ({
      good: { border: 'border-lime/30', text: 'text-lime', glow: 'bg-lime/20' },
      bad: { border: 'border-rose/35', text: 'text-rose', glow: 'bg-rose/20' },
      unsure: { border: 'border-amber/35', text: 'text-amber', glow: 'bg-amber/20' },
    })[tone.value],
)
const tabs = computed(() => {
  if (!advice.value) return []
  if (prediction.value.healthy) {
    return [
      { id: 'organic', label: t('scan.care'), icon: Sprout, items: advice.value.organic },
      { id: 'prevention', label: t('scan.prevention'), icon: ShieldCheck, items: advice.value.prevention },
    ]
  }
  return [
    { id: 'organic', label: t('scan.organic'), icon: Sprout, items: advice.value.organic },
    { id: 'chemical', label: t('scan.chemical'), icon: FlaskConical, items: advice.value.chemical },
    { id: 'prevention', label: t('scan.prevention'), icon: ShieldCheck, items: advice.value.prevention },
  ]
})
const activeItems = computed(() => tabs.value.find((tab) => tab.id === activeTab.value)?.items || [])
const threshold = computed(() => Math.round((result.value?.threshold ?? 0.7) * 100))

// ----- camera -----
const cameraOpen = ref(false)
const cameraError = ref(false)
const video = ref(null)
let stream = null

async function openCamera() {
  cameraError.value = false
  cameraOpen.value = true
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
    await nextTick()
    if (video.value) {
      video.value.srcObject = stream
      await video.value.play()
    }
  } catch {
    cameraError.value = true
  }
}

function closeCamera() {
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
  cameraOpen.value = false
}

function capture() {
  const element = video.value
  if (!element?.videoWidth) return
  const canvas = document.createElement('canvas')
  canvas.width = element.videoWidth
  canvas.height = element.videoHeight
  canvas.getContext('2d').drawImage(element, 0, 0)
  canvas.toBlob(
    (blob) => {
      closeCamera()
      if (blob) analyse(new File([blob], 'camera.jpg', { type: 'image/jpeg' }))
    },
    'image/jpeg',
    0.92,
  )
}

onBeforeUnmount(() => {
  closeCamera()
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<template>
  <div>
    <header>
      <h1 class="font-display text-4xl font-bold text-fog sm:text-5xl">{{ t('scan.title') }}</h1>
      <p class="mt-2 text-lg text-mist">{{ t('scan.subtitle') }}</p>
    </header>

    <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" class="hidden" data-testid="file-input" @change="onFileChosen" />

    <div class="mt-8 grid items-start gap-6 xl:grid-cols-[1fr_1.2fr]">
      <!-- ================= Photo ================= -->
      <div class="space-y-5">
        <!-- drop zone -->
        <div
          v-if="!previewUrl"
          class="dropzone"
          :class="{ dragging }"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <span class="icon-tile animate-float !size-20 !rounded-3xl"><ImagePlus class="size-9" /></span>
          <p class="mt-6 text-xl font-semibold text-fog">{{ t('scan.drop') }}</p>
          <p class="mt-1 text-mist">{{ t('scan.or') }}</p>
          <div class="mt-5 flex w-full max-w-sm flex-col gap-3 sm:flex-row">
            <button type="button" class="btn btn-primary btn-lg flex-1" @click="fileInput.click()">
              <ImagePlus class="size-5" /> {{ t('scan.choose') }}
            </button>
            <button type="button" class="btn btn-ghost btn-lg flex-1" @click="openCamera">
              <Camera class="size-5" /> {{ t('scan.camera') }}
            </button>
          </div>
          <p class="mt-5 text-sm text-dim">{{ t('scan.formats') }}</p>
        </div>

        <!-- the chosen photo -->
        <div v-else class="glass overflow-hidden rounded-[2rem] p-3">
          <div class="relative overflow-hidden rounded-[1.5rem]">
            <img :src="previewUrl" alt="" class="aspect-square w-full object-cover" />
            <template v-if="status === 'loading'">
              <div class="absolute inset-0 bg-ink-950/35" />
              <div class="photo-scan" />
              <div class="absolute inset-x-0 bottom-0 flex items-center justify-center gap-3 bg-gradient-to-t from-ink-950/90 to-transparent pb-5 pt-12 text-lg font-semibold text-fog">
                <ScanLine class="size-5 animate-pulse text-lime" /> {{ t('scan.analysing') }}
              </div>
            </template>
          </div>
          <button type="button" class="btn btn-ghost mt-3 w-full" :disabled="status === 'loading'" @click="reset">
            <RotateCcw class="size-5" /> {{ t('scan.again') }}
          </button>
        </div>

        <!-- tips -->
        <div class="glass rounded-3xl p-6">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-dim">{{ t('scan.tipsTitle') }}</h2>
          <ul class="mt-4 grid gap-3 sm:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
            <li v-for="tip in [{ icon: Leaf, key: 'tip1' }, { icon: Square, key: 'tip2' }, { icon: Sun, key: 'tip3' }]" :key="tip.key" class="flex items-center gap-3">
              <span class="grid size-10 shrink-0 place-items-center rounded-xl bg-lime/10 text-lime"><component :is="tip.icon" class="size-5" /></span>
              <span class="font-medium text-fog">{{ t(`scan.${tip.key}`) }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- ================= Result ================= -->
      <div aria-live="polite">
        <!-- nothing yet -->
        <div v-if="status === 'idle'" class="glass grid min-h-[26rem] place-items-center rounded-[2rem] p-8 text-center">
          <div>
            <span class="icon-tile muted mx-auto !size-20 !rounded-3xl"><ScanLine class="size-9" /></span>
            <p class="mt-6 text-2xl font-semibold text-fog">{{ t('scan.waiting') }}</p>
            <p class="mt-1 text-mist">{{ t('scan.waitingText') }}</p>
          </div>
        </div>

        <!-- waiting for the model -->
        <div v-else-if="status === 'loading'" class="glass min-h-[26rem] space-y-5 rounded-[2rem] p-8">
          <div class="flex items-center gap-6">
            <div class="size-40 shrink-0 animate-pulse rounded-full bg-white/8" />
            <div class="flex-1 space-y-4">
              <div class="h-5 w-24 animate-pulse rounded bg-white/8" />
              <div class="h-9 w-3/4 animate-pulse rounded-lg bg-white/10" />
              <div class="h-9 w-1/2 animate-pulse rounded-lg bg-white/10" />
            </div>
          </div>
          <div class="h-24 animate-pulse rounded-2xl bg-white/6" />
          <div class="h-24 animate-pulse rounded-2xl bg-white/6" />
        </div>

        <!-- something went wrong -->
        <div v-else-if="status === 'error'" class="glass rounded-[2rem] border-rose/35 p-8 text-center" data-testid="scan-error">
          <span class="mx-auto grid size-16 place-items-center rounded-2xl bg-rose/15 text-rose"><CircleAlert class="size-8" /></span>
          <p class="mx-auto mt-5 max-w-md text-xl font-semibold text-fog">{{ t(`errors.${errorCode}`) }}</p>
          <button type="button" class="btn btn-primary mt-6" @click="reset"><RotateCcw class="size-5" /> {{ t('scan.again') }}</button>
        </div>

        <!-- the result -->
        <div v-else-if="result" class="space-y-5" data-testid="scan-result">
          <section class="animate-rise glass relative overflow-hidden rounded-[2rem] p-7 sm:p-8" :class="toneClasses.border">
            <div class="glow -right-20 -top-24 size-72" :class="toneClasses.glow" />
            <div class="relative flex flex-col items-center gap-7 text-center sm:flex-row sm:text-left">
              <ConfidenceRing :value="prediction.confidence" :tone="tone" :label="t('scan.confidence')" />
              <div class="min-w-0">
                <div class="text-sm font-semibold uppercase tracking-wider text-dim">{{ t('scan.crop') }}</div>
                <div class="font-display text-2xl font-bold text-fog" data-testid="result-crop">{{ cropName(prediction.crop, true) }}</div>
                <div class="mt-4 text-sm font-semibold uppercase tracking-wider text-dim">{{ t('scan.result') }}</div>
                <div class="font-display text-3xl font-extrabold leading-tight sm:text-4xl" :class="toneClasses.text" data-testid="result-condition">
                  {{ prediction.healthy ? t('scan.healthyLeaf') : prediction.condition }}
                </div>
              </div>
            </div>
          </section>

          <!-- below 70%: do not rely on the result -->
          <section
            v-if="result.low_confidence"
            class="animate-rise flex gap-4 rounded-3xl border border-amber/40 bg-amber/10 p-5 sm:p-6"
            style="animation-delay: 80ms"
            role="alert"
            data-testid="low-confidence"
          >
            <AlertTriangle class="mt-0.5 size-7 shrink-0 text-amber" />
            <div>
              <h2 class="text-lg font-bold text-amber">{{ t('scan.lowTitle') }}</h2>
              <p class="mt-1 leading-relaxed text-fog/90">{{ t('scan.lowText', { threshold }) }}</p>
            </div>
          </section>

          <template v-if="advice">
            <section v-if="advice.symptoms" class="animate-rise grid gap-4 sm:grid-cols-2" style="animation-delay: 140ms">
              <div class="glass rounded-3xl p-5">
                <h2 class="text-sm font-semibold uppercase tracking-wider text-dim">{{ t('scan.symptoms') }}</h2>
                <p class="mt-2 leading-relaxed text-fog">{{ advice.symptoms }}</p>
              </div>
              <div class="glass rounded-3xl p-5">
                <h2 class="text-sm font-semibold uppercase tracking-wider text-dim">{{ t('scan.cause') }}</h2>
                <p class="mt-2 leading-relaxed text-fog">{{ advice.cause }}</p>
              </div>
            </section>

            <section class="animate-rise glass rounded-[2rem] p-5 sm:p-6" style="animation-delay: 200ms">
              <div class="flex gap-2 overflow-x-auto rounded-2xl bg-ink-950/50 p-1.5" role="tablist">
                <button
                  v-for="tab in tabs"
                  :key="tab.id"
                  type="button"
                  role="tab"
                  :aria-selected="activeTab === tab.id"
                  class="tab"
                  :class="{ active: activeTab === tab.id }"
                  @click="activeTab = tab.id"
                >
                  <component :is="tab.icon" class="size-5" /> {{ tab.label }}
                </button>
              </div>
              <ol class="mt-4 space-y-3">
                <li v-for="(item, index) in activeItems" :key="`${activeTab}-${index}`" class="step" :style="{ animationDelay: `${index * 70}ms` }">
                  <span class="step-number" :class="activeTab">{{ index + 1 }}</span>
                  <span class="text-[1.05rem] leading-relaxed text-fog">{{ item }}</span>
                </li>
              </ol>
            </section>
          </template>
          <p v-else class="glass rounded-3xl p-5 text-mist">{{ t('scan.noAdvice') }}</p>

          <section class="animate-rise glass rounded-3xl p-5 sm:p-6" style="animation-delay: 260ms">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-dim">{{ t('scan.others') }}</h2>
            <div class="mt-4 space-y-4">
              <div v-for="option in result.alternatives" :key="option.class_name">
                <div class="flex items-baseline justify-between gap-4">
                  <span class="truncate font-medium text-fog">
                    {{ cropName(option.crop) }} · {{ option.healthy ? t('scan.healthyLeaf') : option.condition }}
                  </span>
                  <span class="font-display font-bold tabular-nums text-mist">{{ (option.confidence * 100).toFixed(1) }}%</span>
                </div>
                <div class="mt-2 h-2 overflow-hidden rounded-full bg-white/8">
                  <div class="bar h-full rounded-full bg-gradient-to-r from-leaf to-lime" :style="{ width: `${option.confidence * 100}%` }" />
                </div>
              </div>
            </div>
          </section>

          <p class="rounded-2xl border border-dashed border-white/15 px-5 py-4 text-sm leading-relaxed text-mist">
            {{ t('scan.disclaimer') }}
          </p>
        </div>
      </div>
    </div>

    <!-- ================= Camera ================= -->
    <Teleport to="body">
      <div v-if="cameraOpen" class="fixed inset-0 z-[60] grid place-items-center bg-ink-950/85 p-4 backdrop-blur-md" @keydown.esc="closeCamera">
        <div class="glass w-full max-w-xl rounded-[2rem] bg-ink-900/90 p-4">
          <div class="relative aspect-[4/3] overflow-hidden rounded-[1.5rem] bg-ink-950">
            <video ref="video" class="size-full object-cover" playsinline muted />
            <p v-if="cameraError" class="absolute inset-0 grid place-items-center p-8 text-center text-lg text-fog">
              {{ t('scan.cameraError') }}
            </p>
            <div v-else class="pointer-events-none absolute inset-8 rounded-3xl border-2 border-dashed border-lime/60" />
          </div>
          <div class="mt-4 flex gap-3">
            <button type="button" class="btn btn-ghost flex-1" @click="closeCamera"><X class="size-5" /> {{ t('scan.cancel') }}</button>
            <button v-if="!cameraError" type="button" class="btn btn-primary flex-[2]" @click="capture">
              <Camera class="size-5" /> {{ t('scan.capture') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 26rem;
  padding: 2.5rem 1.5rem;
  border-radius: 2rem;
  border: 2px dashed rgb(185 245 81 / 0.3);
  background:
    radial-gradient(420px circle at 50% 0%, rgb(185 245 81 / 0.1), transparent 70%),
    rgb(255 255 255 / 0.03);
  text-align: center;
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    transform 0.3s var(--ease-out-expo);
}
.dropzone.dragging {
  border-color: var(--color-lime);
  background:
    radial-gradient(420px circle at 50% 0%, rgb(185 245 81 / 0.22), transparent 70%),
    rgb(185 245 81 / 0.06);
  transform: scale(1.012);
}

/* the scan line that sweeps over the photo while the model works */
.photo-scan {
  position: absolute;
  left: 0;
  right: 0;
  height: 22%;
  background: linear-gradient(180deg, transparent, rgb(185 245 81 / 0.3));
  border-bottom: 3px solid var(--color-lime);
  box-shadow: 0 10px 34px -2px var(--color-lime);
  animation: scan-sweep 1.5s cubic-bezier(0.5, 0, 0.5, 1) infinite alternate;
}

.tab {
  display: inline-flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 3rem;
  padding: 0 1rem;
  border-radius: 0.85rem;
  font-weight: 650;
  white-space: nowrap;
  color: var(--color-mist);
  transition:
    background 0.2s ease,
    color 0.2s ease;
}
.tab:hover {
  color: var(--color-fog);
}
.tab.active {
  color: var(--color-ink-950);
  background: linear-gradient(180deg, #d2fb7c, var(--color-lime));
  box-shadow: 0 10px 24px -10px rgb(185 245 81 / 0.7);
}

.step {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem 1.1rem;
  border-radius: 1.1rem;
  border: 1px solid rgb(255 255 255 / 0.07);
  background: rgb(255 255 255 / 0.035);
  animation: fade-up 0.5s var(--ease-out-expo) both;
}
.step-number {
  display: grid;
  place-items: center;
  flex: none;
  width: 2rem;
  height: 2rem;
  border-radius: 0.65rem;
  font-family: var(--font-display);
  font-weight: 800;
  color: var(--color-ink-950);
  background: var(--color-lime);
}
.step-number.chemical {
  background: var(--color-amber);
}
.step-number.prevention {
  background: var(--color-sky);
}
.bar {
  transform-origin: left;
  animation: grow 0.9s var(--ease-out-expo) both;
}
@keyframes grow {
  from {
    transform: scaleX(0);
  }
}
</style>
