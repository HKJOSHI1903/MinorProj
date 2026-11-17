// The farmer's recent scans, kept in the browser (localStorage). Nothing is sent to a server.

import { ref } from 'vue'

const KEY = 'kisan.scans.v1'
const MAX_SCANS = 30

function read() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(saved) ? saved : []
  } catch {
    return []
  }
}

export const scans = ref(read())

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(scans.value))
  } catch {
    // storage full or blocked: the list still works for this visit
  }
}

export function addScan(result, thumbnail) {
  scans.value = [
    {
      id: Date.now(),
      at: new Date().toISOString(),
      thumbnail,
      crop: result.prediction.crop,
      condition: result.prediction.condition,
      healthy: result.prediction.healthy,
      confidence: result.prediction.confidence,
      lowConfidence: result.low_confidence,
    },
    ...scans.value,
  ].slice(0, MAX_SCANS)
  save()
}

export function clearScans() {
  scans.value = []
  save()
}

// A small square JPEG of the photo for the history list.
export function makeThumbnail(file, size = 112) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = canvas.height = size
      const side = Math.min(image.width, image.height)
      canvas
        .getContext('2d')
        .drawImage(image, (image.width - side) / 2, (image.height - side) / 2, side, side, 0, 0, size, size)
      URL.revokeObjectURL(url)
      resolve(canvas.toDataURL('image/jpeg', 0.72))
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      resolve('')
    }
    image.src = url
  })
}
