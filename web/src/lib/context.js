// The farmer's latest result (a leaf scan or a crop recommendation).
// The assistant page reads it so "what should I do about this?" needs no retyping.
// Kept for the browser tab only (sessionStorage).

import { ref } from 'vue'

const KEY = 'kisan.context.v1'

function read() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) || 'null')
  } catch {
    return null
  }
}

export const lastResult = ref(read())

export function setLastResult(result) {
  lastResult.value = result
  try {
    if (result) sessionStorage.setItem(KEY, JSON.stringify(result))
    else sessionStorage.removeItem(KEY)
  } catch {
    // storage blocked: the result still works until the page is closed
  }
}

export function diseaseContext(response) {
  return {
    type: 'disease',
    crop: response.prediction.crop,
    condition: response.prediction.condition,
    healthy: response.prediction.healthy,
    confidence: response.prediction.confidence,
    low_confidence: response.low_confidence,
  }
}

export function cropContext(response) {
  return {
    type: 'crop',
    crop: response.recommendation.crop,
    confidence: response.recommendation.confidence,
    low_confidence: response.low_confidence,
    inputs: response.inputs,
  }
}
