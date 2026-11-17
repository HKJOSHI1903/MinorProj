// Voice for farmers who would rather listen and speak than read and type.
// Uses the browser's built-in speech features, so nothing is installed and
// no audio is sent to our server. Support varies: reading aloud works in most
// browsers; voice typing works in Chrome, Edge and Android browsers.

import { ref } from 'vue'

const VOICE_LOCALE = { hi: 'hi-IN', en: 'en-IN' }

export const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window
export const speaking = ref(false)

// Reads the parts aloud one after another. Each part is { text, lang } with lang 'hi' or 'en',
// so Hindi labels and English advice are each read with the right voice.
export function speak(parts) {
  if (!canSpeak) return
  stopSpeaking()
  const queue = parts.filter((part) => part.text?.trim())
  if (!queue.length) return
  speaking.value = true
  queue.forEach((part, index) => {
    const utterance = new SpeechSynthesisUtterance(part.text)
    utterance.lang = VOICE_LOCALE[part.lang] || VOICE_LOCALE.en
    utterance.rate = 0.95
    if (index === queue.length - 1) {
      utterance.onend = () => (speaking.value = false)
      utterance.onerror = () => (speaking.value = false)
    }
    window.speechSynthesis.speak(utterance)
  })
}

export function stopSpeaking() {
  if (!canSpeak) return
  window.speechSynthesis.cancel()
  speaking.value = false
}

const Recognition = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null
export const canListen = Boolean(Recognition)

// Starts voice typing. onText receives the words heard so far; onEnd is called when it stops.
// Returns a function that stops listening.
export function listen({ lang, onText, onEnd }) {
  if (!Recognition) return () => {}
  const recognition = new Recognition()
  recognition.lang = VOICE_LOCALE[lang] || VOICE_LOCALE.en
  recognition.interimResults = true
  recognition.continuous = false
  recognition.onresult = (event) => {
    onText(Array.from(event.results, (result) => result[0].transcript).join(' '))
  }
  recognition.onend = () => onEnd?.()
  recognition.onerror = () => onEnd?.()
  recognition.start()
  return () => recognition.stop()
}
