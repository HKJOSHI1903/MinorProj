<script>
// The conversation is kept outside the component, so it is still there when the
// farmer goes to another page and comes back.
import { ref } from 'vue'

const messages = ref([]) // { id, role: 'user' | 'assistant', text, mode, sources, passages, notice }
</script>

<script setup>
// Module 3: the farming assistant. Questions go to the server, which finds the
// matching passages in the knowledge base and (with an API key) has Claude write the answer.
import { ArrowUp, BookOpen, Leaf, Mic, PhoneCall, Plus, Sparkles, Sprout, Volume2, VolumeX, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted } from 'vue'
import { chatStatus, sendChat } from '../../lib/api'
import { lastResult, setLastResult } from '../../lib/context'
import { useI18n } from '../../lib/i18n'
import { canListen, canSpeak, listen, speak, speaking, stopSpeaking } from '../../lib/speech'

const { t, lang, cropName, advisorCropName } = useI18n()

const draft = ref('')
const busy = ref(false)
const status = ref(null) // { ai_available, documents, helpline }
const listening = ref(false)
const speakingId = ref(null)
const thread = ref(null)
let stopListening = null

onMounted(async () => {
  try {
    status.value = await chatStatus()
  } catch {
    status.value = null
  }
  scrollToEnd()
})

// A one-line description of the scan or crop result the question is about.
const contextLabel = computed(() => {
  const context = lastResult.value
  if (!context) return ''
  if (context.type === 'disease') {
    return `${cropName(context.crop)} · ${context.healthy ? t('scan.healthyLeaf') : context.condition}`
  }
  return `${t('crop.best')}: ${advisorCropName(context.crop)}`
})

const suggestions = computed(() => [
  ...(lastResult.value ? ['qContext'] : []),
  'q1', 'q2', 'q3', 'q4', 'q5', 'q6',
])

async function scrollToEnd() {
  await nextTick()
  thread.value?.scrollTo({ top: thread.value.scrollHeight, behavior: 'smooth' })
}

async function send(text = draft.value) {
  const question = text.trim()
  if (!question || busy.value) return
  stopSpeaking()
  stopListening?.()

  // Earlier turns give the assistant the thread of the conversation.
  const history = messages.value
    .filter((message) => message.text)
    .map((message) => ({ role: message.role, content: message.text }))

  messages.value.push({ id: Date.now(), role: 'user', text: question })
  draft.value = ''
  busy.value = true
  scrollToEnd()

  try {
    const reply = await sendChat({ message: question, language: lang.value, history, context: lastResult.value })
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      mode: reply.mode,
      text: reply.mode === 'ai' ? reply.answer : '',
      sources: reply.sources,
      passages: reply.passages,
      notice: reply.notice,
    })
  } catch {
    messages.value.push({ id: Date.now() + 1, role: 'assistant', mode: 'error' })
  } finally {
    busy.value = false
    scrollToEnd()
  }
}

function newChat() {
  stopSpeaking()
  messages.value = []
}

// ----- voice -----
function toggleMic() {
  if (listening.value) return stopListening?.()
  listening.value = true
  stopListening = listen({
    lang: lang.value,
    onText: (text) => (draft.value = text),
    onEnd: () => {
      listening.value = false
      stopListening = null
    },
  })
}

function readAloud(message) {
  if (speaking.value && speakingId.value === message.id) {
    speakingId.value = null
    return stopSpeaking()
  }
  speakingId.value = message.id
  if (message.mode === 'ai') speak([{ text: message.text, lang: lang.value }])
  else if (message.mode === 'passages') speak(message.passages.map((passage) => ({ text: passage.text, lang: 'en' })))
  else speak([{ text: t('assistant.noMatch'), lang: lang.value }])
}

onBeforeUnmount(() => {
  stopSpeaking()
  stopListening?.()
})
</script>

<template>
  <div class="flex min-h-[calc(100dvh-13rem)] flex-col lg:min-h-[calc(100dvh-5rem)]">
    <header class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="font-display text-4xl font-bold text-fog sm:text-5xl">{{ t('assistant.title') }}</h1>
        <p class="mt-2 text-lg text-mist">{{ t('assistant.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="status" class="badge !px-3 !py-1.5 !text-sm" :class="status.ai_available ? 'badge-live' : 'badge-soon'" data-testid="ai-status">
          <Sparkles class="size-4" /> {{ status.ai_available ? t('assistant.aiOn') : t('assistant.aiOff') }}
        </span>
        <button v-if="messages.length" type="button" class="btn btn-ghost !min-h-10 !px-4 !text-sm" @click="newChat">
          <Plus class="size-4" /> {{ t('assistant.clear') }}
        </button>
      </div>
    </header>

    <p v-if="status && !status.ai_available" class="mt-4 rounded-2xl border border-amber/30 bg-amber/8 px-4 py-3 text-sm leading-relaxed text-fog/90">
      {{ t('assistant.aiOffText') }}
    </p>

    <!-- ================= Conversation ================= -->
    <div ref="thread" class="scroll-thin mt-6 flex-1 space-y-5 overflow-y-auto pb-4" aria-live="polite">
      <!-- nothing asked yet -->
      <div v-if="!messages.length" class="grid place-items-center py-6 text-center">
        <span class="icon-tile sky animate-float !size-20 !rounded-3xl"><Sparkles class="size-9" /></span>
        <h2 class="font-display mt-6 text-3xl font-bold text-fog">{{ t('assistant.emptyTitle') }}</h2>
        <p class="mt-6 text-sm font-semibold uppercase tracking-wider text-dim">{{ t('assistant.try') }}</p>
        <div class="mt-3 flex max-w-3xl flex-wrap justify-center gap-2.5">
          <button v-for="key in suggestions" :key="key" type="button" class="suggestion" :class="{ primary: key === 'qContext' }" @click="send(t(`assistant.${key}`))">
            {{ t(`assistant.${key}`) }}
          </button>
        </div>
        <a href="tel:18001801551" class="glass mt-8 flex items-center gap-4 rounded-3xl px-5 py-4 text-left transition-transform duration-300 hover:-translate-y-1">
          <span class="icon-tile !size-12"><PhoneCall class="size-5" /></span>
          <span>
            <span class="block font-semibold text-fog">{{ t('help.title') }}</span>
            <span class="block text-sm text-mist">{{ t('help.call') }}</span>
          </span>
        </a>
      </div>

      <template v-for="message in messages" :key="message.id">
        <!-- the farmer -->
        <div v-if="message.role === 'user'" class="flex justify-end">
          <div class="bubble-user">{{ message.text }}</div>
        </div>

        <!-- the assistant -->
        <div v-else class="flex gap-3" data-testid="assistant-message">
          <span class="mt-1 grid size-10 shrink-0 place-items-center rounded-2xl bg-lime/15 text-lime"><Leaf class="size-5" /></span>
          <div class="min-w-0 max-w-3xl flex-1">
            <div class="bubble-assistant">
              <p v-if="message.mode === 'ai'" class="whitespace-pre-wrap">{{ message.text }}</p>

              <template v-else-if="message.mode === 'passages'">
                <p v-if="message.notice" class="mb-3 text-sm text-amber">{{ message.notice }}</p>
                <p class="font-semibold text-fog">{{ t('assistant.passagesIntro') }}</p>
                <div v-for="(passage, index) in message.passages" :key="index" class="passage">
                  <div class="text-sm font-semibold text-lime">{{ passage.section }}</div>
                  <p class="mt-1">{{ passage.text }}</p>
                </div>
              </template>

              <p v-else-if="message.mode === 'no_match'">{{ t('assistant.noMatch') }}</p>
              <p v-else class="text-rose">{{ t('assistant.error') }}</p>
            </div>

            <div v-if="message.mode !== 'error'" class="mt-2 flex flex-wrap items-center gap-2">
              <button v-if="canSpeak" type="button" class="mini" @click="readAloud(message)">
                <VolumeX v-if="speaking && speakingId === message.id" class="size-4" /><Volume2 v-else class="size-4" />
                {{ speaking && speakingId === message.id ? t('voice.stop') : t('voice.listen') }}
              </button>
              <template v-if="message.sources?.length">
                <span class="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-dim">
                  <BookOpen class="size-3.5" /> {{ t('assistant.sources') }}
                </span>
                <span v-for="source in message.sources.slice(0, 3)" :key="source.title + source.section" class="source" :title="source.title">
                  {{ source.section }}
                </span>
              </template>
            </div>
          </div>
        </div>
      </template>

      <!-- waiting for the answer -->
      <div v-if="busy" class="flex gap-3">
        <span class="mt-1 grid size-10 shrink-0 place-items-center rounded-2xl bg-lime/15 text-lime"><Leaf class="size-5" /></span>
        <div class="bubble-assistant flex items-center gap-3 text-mist">
          <span class="typing"><i /><i /><i /></span> {{ t('assistant.thinking') }}
        </div>
      </div>
    </div>

    <!-- ================= Composer ================= -->
    <div class="composer-dock sticky bottom-24 z-10 lg:bottom-0">
      <div v-if="contextLabel" class="mb-2 flex">
        <span class="glass inline-flex max-w-full items-center gap-2 rounded-full bg-ink-900/90 py-1.5 pl-4 pr-1.5 text-sm" data-testid="chat-context">
          <Sprout class="size-4 shrink-0 text-lime" />
          <span class="text-mist">{{ t('assistant.about') }}:</span>
          <span class="truncate font-semibold text-fog">{{ contextLabel }}</span>
          <button type="button" class="grid size-7 shrink-0 place-items-center rounded-full hover:bg-white/10" :aria-label="t('assistant.clearContext')" @click="setLastResult(null)">
            <X class="size-4" />
          </button>
        </span>
      </div>

      <form class="composer-box flex items-end gap-2 rounded-[1.75rem] p-2" @submit.prevent="send()">
        <button
          v-if="canListen"
          type="button"
          class="round"
          :class="{ live: listening }"
          :aria-label="t('voice.speak')"
          :title="t('voice.speak')"
          @click="toggleMic"
        >
          <Mic class="size-5" />
        </button>
        <textarea
          v-model="draft"
          rows="1"
          class="composer"
          :placeholder="listening ? t('voice.listening') : t('assistant.placeholder')"
          :aria-label="t('assistant.placeholder')"
          data-testid="chat-input"
          @keydown.enter.exact.prevent="send()"
        />
        <button type="submit" class="round send" :disabled="!draft.trim() || busy" :aria-label="t('assistant.send')" data-testid="chat-send">
          <ArrowUp class="size-5" :stroke-width="2.6" />
        </button>
      </form>
      <p class="mt-2 px-2 text-center text-xs text-dim">{{ t('assistant.disclaimer') }}</p>
    </div>
  </div>
</template>

<style scoped>
.bubble-user {
  max-width: min(85%, 36rem);
  padding: 0.85rem 1.15rem;
  border-radius: 1.4rem 1.4rem 0.4rem 1.4rem;
  font-size: 1.08rem;
  font-weight: 500;
  line-height: 1.5;
  color: var(--color-ink-950);
  background: linear-gradient(180deg, #d2fb7c, var(--color-lime));
  box-shadow: 0 14px 30px -14px rgb(185 245 81 / 0.6);
  animation: fade-up 0.4s var(--ease-out-expo) both;
}
.bubble-assistant {
  padding: 1rem 1.2rem;
  border-radius: 0.4rem 1.4rem 1.4rem 1.4rem;
  border: 1px solid rgb(255 255 255 / 0.09);
  background: linear-gradient(160deg, rgb(255 255 255 / 0.07), rgb(255 255 255 / 0.02));
  font-size: 1.08rem;
  line-height: 1.65;
  color: var(--color-fog);
  animation: fade-up 0.4s var(--ease-out-expo) both;
}
.passage {
  margin-top: 0.9rem;
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  border-left: 3px solid var(--color-lime);
  background: rgb(5 13 8 / 0.5);
  font-size: 1rem;
}
.suggestion {
  padding: 0.7rem 1.1rem;
  border-radius: 999px;
  border: 1px solid rgb(255 255 255 / 0.12);
  background: rgb(255 255 255 / 0.04);
  font-size: 1rem;
  font-weight: 500;
  color: var(--color-fog);
  transition:
    transform 0.25s var(--ease-out-expo),
    border-color 0.2s ease,
    background 0.2s ease;
}
.suggestion:hover {
  transform: translateY(-2px);
  border-color: rgb(185 245 81 / 0.5);
  background: rgb(185 245 81 / 0.08);
}
.suggestion.primary {
  border-color: rgb(185 245 81 / 0.5);
  color: var(--color-lime);
}
.mini {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2rem;
  padding: 0 0.75rem;
  border-radius: 999px;
  border: 1px solid rgb(255 255 255 / 0.12);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-mist);
  transition: color 0.2s ease, border-color 0.2s ease;
}
.mini:hover {
  color: var(--color-lime);
  border-color: rgb(185 245 81 / 0.5);
}
.source {
  max-width: 14rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0.2rem 0.7rem;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.06);
  font-size: 0.8rem;
  color: var(--color-mist);
}
/* The dock is solid so messages scrolling underneath never show through the input. */
.composer-dock {
  margin: 0 -0.5rem;
  padding: 1.5rem 0.5rem 0.75rem;
  background: linear-gradient(to top, var(--color-ink-950) 72%, transparent);
}
.composer-box {
  border: 1px solid rgb(255 255 255 / 0.14);
  background: var(--color-ink-800);
  box-shadow: 0 20px 50px -20px rgb(0 0 0 / 0.9);
}
.composer-box:focus-within {
  border-color: rgb(185 245 81 / 0.55);
}
.composer {
  flex: 1;
  min-height: 3rem;
  max-height: 9rem;
  padding: 0.7rem 0.5rem;
  resize: none;
  background: transparent;
  font-size: 1.1rem;
  line-height: 1.5;
  color: var(--color-fog);
  field-sizing: content;
}
.composer::placeholder {
  color: var(--color-dim);
}
.composer:focus {
  outline: none;
}
.round {
  display: grid;
  place-items: center;
  flex: none;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  color: var(--color-fog);
  background: rgb(255 255 255 / 0.08);
  transition:
    background 0.2s ease,
    transform 0.2s var(--ease-out-expo),
    opacity 0.2s ease;
}
.round:hover {
  background: rgb(255 255 255 / 0.16);
}
.round.live {
  color: #fff;
  background: var(--color-rose);
  animation: pulse-ring 1.4s ease-out infinite;
}
.round.send {
  color: var(--color-ink-950);
  background: var(--color-lime);
}
.round.send:hover:not(:disabled) {
  transform: translateY(-2px);
}
.round.send:disabled {
  opacity: 0.35;
}
.typing {
  display: inline-flex;
  gap: 0.3rem;
}
.typing i {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--color-lime);
  animation: bounce 1.1s ease-in-out infinite;
}
.typing i:nth-child(2) {
  animation-delay: 0.15s;
}
.typing i:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-5px); opacity: 1; }
}
@keyframes pulse-ring {
  0% { box-shadow: 0 0 0 0 rgb(255 107 94 / 0.6); }
  100% { box-shadow: 0 0 0 0.9rem rgb(255 107 94 / 0); }
}
</style>
