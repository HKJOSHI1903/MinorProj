<script setup>
import {
  ArrowRight,
  ArrowUpRight,
  CloudRain,
  CloudSun,
  Droplets,
  Leaf,
  LocateFixed,
  MessagesSquare,
  PhoneCall,
  RefreshCw,
  ScanLine,
  Sprout,
  Thermometer,
  Trash2,
  Wind,
} from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { meta } from '../../lib/api'
import { clearScans, scans } from '../../lib/history'
import { useI18n } from '../../lib/i18n'
import { getWeather } from '../../lib/weather'

const { t, cropName } = useI18n()

// Spraying weather. The location is requested only when the farmer presses the button.
const weather = ref(null)
const weatherState = ref('idle') // idle | loading | done | error
const weatherError = ref('')

async function checkWeather() {
  weatherState.value = 'loading'
  try {
    weather.value = await getWeather()
    weatherState.value = 'done'
  } catch (error) {
    weatherError.value = error.message
    weatherState.value = 'error'
  }
}

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return t('overview.morning')
  if (hour < 17) return t('overview.afternoon')
  return t('overview.evening')
})

// Counts come from the scans saved on this device.
const counts = computed(() => ({
  total: scans.value.length,
  healthy: scans.value.filter((scan) => scan.healthy && !scan.lowConfidence).length,
  diseased: scans.value.filter((scan) => !scan.healthy && !scan.lowConfidence).length,
  unsure: scans.value.filter((scan) => scan.lowConfidence).length,
}))

const accuracy = computed(() => {
  const value = meta.value?.metrics?.test_accuracy
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : null
})

function timeAgo(iso) {
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 1) return t('time.now')
  if (minutes < 60) return t('time.min', { n: minutes })
  if (minutes < 60 * 24) return t('time.hour', { n: Math.floor(minutes / 60) })
  return t('time.day', { n: Math.floor(minutes / (60 * 24)) })
}

function tone(scan) {
  if (scan.lowConfidence) return 'text-amber'
  return scan.healthy ? 'text-lime' : 'text-rose'
}
</script>

<template>
  <div>
    <header>
      <h1 class="font-display text-4xl font-bold text-fog sm:text-5xl">{{ greeting }}</h1>
      <p class="mt-2 text-lg text-mist">{{ t('overview.subtitle') }}</p>
    </header>

    <div class="mt-8 grid gap-5 xl:grid-cols-[1.5fr_1fr]">
      <!-- the main action -->
      <RouterLink
        v-tilt="4"
        :to="{ name: 'disease' }"
        class="tilt group relative block overflow-hidden rounded-[2rem] border border-lime/25 bg-gradient-to-br from-ink-600 via-ink-700 to-ink-900 p-7 sm:p-9"
      >
        <div class="glow -right-24 -top-24 size-80 bg-lime/30" />
        <Leaf
          class="absolute -bottom-10 -right-6 size-64 rotate-[-18deg] text-lime/10 transition-transform duration-700 ease-[var(--ease-out-expo)] group-hover:rotate-[-8deg] group-hover:scale-110"
          :stroke-width="0.7"
        />
        <div class="lift relative">
          <span class="icon-tile !size-16 !rounded-2xl"><ScanLine class="size-8" /></span>
          <h2 class="font-display mt-7 text-3xl font-bold text-fog sm:text-4xl">{{ t('overview.scanTitle') }}</h2>
          <p class="mt-2 max-w-md text-lg text-mist">{{ t('overview.scanText') }}</p>
          <span class="btn btn-primary btn-lg mt-7">{{ t('overview.scanButton') }} <ArrowRight class="size-5" /></span>
        </div>
      </RouterLink>

      <!-- numbers -->
      <div class="grid grid-cols-2 gap-4">
        <div class="glass rounded-3xl p-5">
          <div class="text-sm font-medium text-mist">{{ t('overview.scans') }}</div>
          <div class="font-display mt-2 text-5xl font-bold tabular-nums text-fog">{{ counts.total }}</div>
        </div>
        <div class="glass rounded-3xl p-5">
          <div class="text-sm font-medium text-mist">{{ t('overview.healthy') }}</div>
          <div class="font-display mt-2 text-5xl font-bold tabular-nums text-lime">{{ counts.healthy }}</div>
        </div>
        <div class="glass rounded-3xl p-5">
          <div class="text-sm font-medium text-mist">{{ t('overview.diseased') }}</div>
          <div class="font-display mt-2 text-5xl font-bold tabular-nums text-rose">{{ counts.diseased }}</div>
        </div>
        <div class="glass rounded-3xl p-5">
          <div class="text-sm font-medium text-mist">{{ t('overview.accuracy') }}</div>
          <div v-if="accuracy" class="font-display mt-2 text-4xl font-bold tabular-nums text-fog">{{ accuracy }}</div>
          <div v-else class="mt-3 h-9 w-20 animate-pulse rounded-lg bg-white/10" />
          <div class="mt-1 text-xs text-dim">{{ t('overview.accuracyNote') }}</div>
        </div>
      </div>
    </div>

    <div class="mt-5 grid gap-5 xl:grid-cols-[1.5fr_1fr]">
      <!-- recent scans -->
      <section class="glass rounded-[2rem] p-6 sm:p-7">
        <div class="flex items-center justify-between">
          <h2 class="font-display text-2xl font-bold text-fog">{{ t('overview.recent') }}</h2>
          <button
            v-if="scans.length"
            type="button"
            class="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium text-mist transition-colors hover:bg-white/5 hover:text-rose"
            @click="clearScans"
          >
            <Trash2 class="size-4" /> {{ t('overview.clear') }}
          </button>
        </div>

        <ul v-if="scans.length" class="mt-5 divide-y divide-white/8">
          <li v-for="scan in scans.slice(0, 6)" :key="scan.id" class="flex items-center gap-4 py-3.5">
            <img v-if="scan.thumbnail" :src="scan.thumbnail" alt="" class="size-14 shrink-0 rounded-2xl object-cover ring-1 ring-white/10" />
            <span v-else class="icon-tile muted !size-14 shrink-0"><Leaf class="size-6" /></span>
            <div class="min-w-0 flex-1">
              <div class="truncate text-lg font-semibold text-fog">
                {{ scan.healthy ? t('scan.healthyLeaf') : scan.condition }}
              </div>
              <div class="truncate text-sm text-mist">{{ cropName(scan.crop) }} · {{ timeAgo(scan.at) }}</div>
            </div>
            <div class="font-display text-xl font-bold tabular-nums" :class="tone(scan)">
              {{ Math.round(scan.confidence * 100) }}%
            </div>
          </li>
        </ul>

        <div v-else class="grid place-items-center py-12 text-center">
          <span class="icon-tile muted !size-16 !rounded-2xl"><Leaf class="size-7" /></span>
          <div class="mt-4 text-xl font-semibold text-fog">{{ t('overview.empty') }}</div>
          <p class="mt-1 max-w-xs text-mist">{{ t('overview.emptyText') }}</p>
        </div>
      </section>

      <!-- other modules -->
      <section>
        <h2 class="font-display px-1 text-2xl font-bold text-fog">{{ t('overview.modules') }}</h2>
        <div class="mt-4 space-y-4">
          <RouterLink
            v-for="module in [
              { name: 'crop', icon: Sprout, tile: 'amber', title: 'app.crop', text: 'features.crop.text' },
              { name: 'assistant', icon: MessagesSquare, tile: 'sky', title: 'app.assistant', text: 'features.assistant.text' },
            ]"
            :key="module.name"
            :to="{ name: module.name }"
            class="glass group flex items-center gap-4 rounded-3xl p-5 transition-transform duration-300 ease-[var(--ease-out-expo)] hover:-translate-y-1"
          >
            <span class="icon-tile" :class="module.tile"><component :is="module.icon" class="size-6" /></span>
            <div class="min-w-0 flex-1">
              <div class="text-lg font-semibold text-fog">{{ t(module.title) }}</div>
              <div class="truncate text-sm text-mist">{{ t(module.text) }}</div>
            </div>
            <ArrowUpRight class="size-5 text-mist transition-colors group-hover:text-lime" />
          </RouterLink>

          <!-- spraying weather -->
          <div class="glass rounded-3xl p-5" data-testid="weather-card">
            <div class="flex items-center gap-4">
              <span class="icon-tile muted"><CloudSun class="size-6" /></span>
              <div class="min-w-0 flex-1">
                <div class="text-lg font-semibold text-fog">{{ t('weather.title') }}</div>
                <div v-if="weatherState !== 'done'" class="text-sm text-mist">{{ t('weather.text') }}</div>
              </div>
              <button
                v-if="weatherState === 'done'"
                type="button"
                class="grid size-10 place-items-center rounded-full border border-white/10 text-mist hover:text-fog"
                :aria-label="t('weather.again')"
                @click="checkWeather"
              >
                <RefreshCw class="size-4" />
              </button>
            </div>

            <template v-if="weatherState === 'done'">
              <div class="mt-4 rounded-2xl border p-4" :class="weather.sprayOk ? 'border-lime/30 bg-lime/8' : 'border-amber/35 bg-amber/10'">
                <div class="flex items-center gap-2 text-lg font-bold" :class="weather.sprayOk ? 'text-lime' : 'text-amber'">
                  <component :is="weather.sprayOk ? Sprout : CloudRain" class="size-5" />
                  {{ weather.sprayOk ? t('weather.good') : t('weather.wait') }}
                </div>
                <p class="mt-1 text-fog/90">{{ t(`weather.${weather.reason}`) }}</p>
              </div>
              <dl class="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div v-for="item in [
                  { icon: Thermometer, label: 'weather.temperature', value: `${Math.round(weather.temperature)}°C` },
                  { icon: Droplets, label: 'weather.humidity', value: `${Math.round(weather.humidity)}%` },
                  { icon: Wind, label: 'weather.wind_label', value: `${Math.round(weather.wind)} km/h` },
                  { icon: CloudRain, label: 'weather.rain_label', value: `${Math.round(weather.rainChance)}%` },
                ]" :key="item.label" class="flex items-center gap-2.5">
                  <component :is="item.icon" class="size-4 shrink-0 text-lime" />
                  <dt class="text-mist">{{ t(item.label) }}</dt>
                  <dd class="ml-auto font-semibold tabular-nums text-fog">{{ item.value }}</dd>
                </div>
              </dl>
              <p class="mt-3 text-xs leading-relaxed text-dim">{{ t('weather.note') }}</p>
            </template>
            <template v-else>
              <p v-if="weatherState === 'error'" class="mt-3 text-sm text-amber" role="alert">{{ t(`weather.${weatherError}`) }}</p>
              <button type="button" class="btn btn-ghost mt-4 w-full" :disabled="weatherState === 'loading'" @click="checkWeather">
                <LocateFixed class="size-5" :class="{ 'animate-pulse': weatherState === 'loading' }" />
                {{ weatherState === 'loading' ? t('weather.checking') : t('weather.button') }}
              </button>
            </template>
          </div>

          <!-- helpline -->
          <a href="tel:18001801551" class="glass group flex items-center gap-4 rounded-3xl p-5 transition-transform duration-300 ease-[var(--ease-out-expo)] hover:-translate-y-1">
            <span class="icon-tile"><PhoneCall class="size-6" /></span>
            <div class="min-w-0 flex-1">
              <div class="text-lg font-semibold text-fog">{{ t('help.title') }}</div>
              <div class="text-sm text-mist">{{ t('help.text') }}</div>
              <div class="mt-1 font-display text-lg font-bold text-lime">1800-180-1551</div>
            </div>
          </a>
        </div>
      </section>
    </div>
  </div>
</template>
