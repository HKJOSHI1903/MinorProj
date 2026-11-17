// All calls to the Python server go through this file.

import { ref } from 'vue'

export class ApiError extends Error {
  constructor(code, message) {
    super(message)
    this.code = code // e.g. "invalid_image"; used to pick the translated message
  }
}

async function request(path, options) {
  let response
  try {
    response = await fetch(path, options)
  } catch {
    throw new ApiError('offline', 'The server cannot be reached.')
  }
  let body = null
  try {
    body = await response.json()
  } catch {
    // not JSON: handled below
  }
  if (!response.ok || body === null) {
    const error = body?.error
    const failure = new ApiError(error?.code || 'server_error', error?.message || `Server error (${response.status})`)
    failure.field = error?.field // which form field was wrong, when the server names one
    throw failure
  }
  return body
}

export function predictDisease(file) {
  const form = new FormData()
  form.append('image', file, file.name || 'leaf.jpg')
  return request('/api/disease/predict', { method: 'POST', body: form })
}

const json = (body) => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

// ---- Module 2: crop recommendation ----
export const cropMeta = ref(null)
let cropMetaPromise = null

export function loadCropMeta() {
  if (!cropMetaPromise) {
    cropMetaPromise = request('/api/crop/meta')
      .then((data) => (cropMeta.value = data))
      .catch(() => {
        cropMetaPromise = null
        return null
      })
  }
  return cropMetaPromise
}

export function recommendCrop(values) {
  return request('/api/crop/recommend', json(values))
}

// ---- Module 3: the assistant ----
export function chatStatus() {
  return request('/api/chat/status')
}

export function sendChat({ message, language, history, context }) {
  return request('/api/chat', json({ message, language, history, context }))
}

// Model facts (classes, crops, real accuracy) are fetched once and shared by every page.
export const meta = ref(null)
export const serverOnline = ref(null) // null = not checked yet
let metaPromise = null

export function loadMeta() {
  if (!metaPromise) {
    metaPromise = request('/api/meta')
      .then((data) => {
        meta.value = data
        serverOnline.value = true
        return data
      })
      .catch(() => {
        serverOnline.value = false
        metaPromise = null // try again next time
        return null
      })
  }
  return metaPromise
}
