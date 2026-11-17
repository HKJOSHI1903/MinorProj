<script setup>
// The frame around every dashboard page: sidebar on desktop, bottom bar on phones.
import { ArrowLeft, LayoutGrid, MessagesSquare, ScanLine, Sprout } from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppLogo from '../../components/AppLogo.vue'
import LangToggle from '../../components/LangToggle.vue'
import { loadMeta, meta, serverOnline } from '../../lib/api'
import { useI18n } from '../../lib/i18n'

const { t } = useI18n()
const route = useRoute()

const items = [
  { name: 'overview', key: 'app.overview', icon: LayoutGrid },
  { name: 'disease', key: 'app.disease', icon: ScanLine },
  { name: 'crop', key: 'app.crop', icon: Sprout, soon: true },
  { name: 'assistant', key: 'app.assistant', icon: MessagesSquare, soon: true },
]

onMounted(loadMeta)

const status = computed(() => {
  if (serverOnline.value === null) return { text: t('app.checking'), tone: 'text-mist' }
  if (serverOnline.value && meta.value) return { text: t('app.online'), tone: 'text-lime' }
  return { text: t('app.offline'), tone: 'text-rose' }
})
</script>

<template>
  <div class="relative min-h-dvh">
    <div class="backdrop fixed">
      <div class="glow -top-48 left-[20%] size-[520px] bg-leaf/25" />
      <div class="glow bottom-[-25%] right-[-8%] size-[460px] bg-lime/10" style="animation-delay: -8s" />
    </div>

    <!-- ===== Sidebar (desktop) ===== -->
    <aside class="fixed inset-y-0 left-0 z-40 hidden w-80 flex-col p-4 lg:flex">
      <div class="glass flex h-full flex-col rounded-3xl bg-ink-900/60 p-5">
        <RouterLink :to="{ name: 'home' }" class="px-1 py-1"><AppLogo /></RouterLink>

        <nav class="mt-9 flex flex-col gap-1.5">
          <RouterLink
            v-for="item in items"
            :key="item.name"
            :to="{ name: item.name }"
            class="nav-item"
            :class="{ active: route.name === item.name }"
          >
            <component :is="item.icon" class="size-5 shrink-0" />
            <span class="flex-1 whitespace-nowrap">{{ t(item.key) }}</span>
            <span v-if="item.soon" class="badge badge-soon !px-2 !py-0.5 !text-[0.68rem]">{{ t('app.soon') }}</span>
          </RouterLink>
        </nav>

        <div class="mt-auto space-y-4">
          <div class="flex items-center gap-2.5 rounded-2xl border border-white/8 bg-white/4 px-4 py-3 text-sm font-medium" :class="status.tone">
            <span class="dot" /> {{ status.text }}
          </div>
          <div class="flex items-center justify-between">
            <LangToggle />
            <RouterLink
              :to="{ name: 'home' }"
              class="grid size-10 place-items-center rounded-full border border-white/10 bg-white/5 text-mist transition-colors hover:text-fog"
              :title="t('app.site')"
              :aria-label="t('app.site')"
            >
              <ArrowLeft class="size-4" />
            </RouterLink>
          </div>
        </div>
      </div>
    </aside>

    <!-- ===== Top bar (phones and tablets) ===== -->
    <header class="glass sticky top-0 z-40 flex h-16 items-center justify-between !rounded-none !border-x-0 !border-t-0 bg-ink-950/75 px-4 lg:hidden">
      <RouterLink :to="{ name: 'home' }"><AppLogo /></RouterLink>
      <LangToggle />
    </header>

    <!-- ===== Page ===== -->
    <main class="relative px-4 pb-32 pt-6 sm:px-6 lg:ml-80 lg:px-10 lg:pb-12 lg:pt-10">
      <div class="mx-auto max-w-6xl">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" :key="route.name" />
          </Transition>
        </RouterView>
      </div>
    </main>

    <!-- ===== Bottom bar (phones and tablets) ===== -->
    <nav class="fixed inset-x-3 bottom-3 z-40 lg:hidden" style="padding-bottom: env(safe-area-inset-bottom)">
      <div class="glass grid grid-cols-4 rounded-3xl bg-ink-900/85 p-1.5">
        <RouterLink
          v-for="item in items"
          :key="item.name"
          :to="{ name: item.name }"
          class="tab-item"
          :class="{ active: route.name === item.name }"
        >
          <component :is="item.icon" class="size-6" />
          <span class="truncate">{{ t(item.key) }}</span>
        </RouterLink>
      </div>
    </nav>
  </div>
</template>

<style scoped>
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-height: 3.25rem;
  padding: 0 1rem;
  border-radius: 1rem;
  border: 1px solid transparent;
  font-size: 1.02rem;
  font-weight: 550;
  color: var(--color-mist);
  transition:
    background 0.2s ease,
    color 0.2s ease,
    transform 0.25s var(--ease-out-expo);
}
.nav-item:hover {
  color: var(--color-fog);
  background: rgb(255 255 255 / 0.05);
  transform: translateX(3px);
}
.nav-item.active {
  color: var(--color-ink-950);
  background: linear-gradient(180deg, #d2fb7c, var(--color-lime));
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.6),
    0 14px 30px -12px rgb(185 245 81 / 0.6);
  transform: none;
}
.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  min-height: 3.75rem;
  min-width: 0;
  padding: 0 0.25rem;
  border-radius: 1.25rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-mist);
  transition:
    background 0.2s ease,
    color 0.2s ease;
}
.tab-item.active {
  color: var(--color-ink-950);
  background: var(--color-lime);
}
.page-enter-active,
.page-leave-active {
  transition:
    opacity 0.28s ease,
    transform 0.4s var(--ease-out-expo);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(14px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
