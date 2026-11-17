<script setup>
// Mounts the Three.js leaf scene. Three.js is loaded only when this component is
// shown, and a still illustration is used if the browser has no WebGL.
import { Leaf } from 'lucide-vue-next'
import { onBeforeUnmount, onMounted, ref } from 'vue'

const container = ref(null)
const failed = ref(false)
let scene = null
let unmounted = false

onMounted(async () => {
  try {
    const { createLeafScene } = await import('../three/LeafScene.js')
    if (unmounted) return
    scene = createLeafScene(container.value)
  } catch {
    failed.value = true
  }
})

onBeforeUnmount(() => {
  unmounted = true
  scene?.dispose()
})
</script>

<template>
  <div ref="container" class="absolute inset-0" aria-hidden="true">
    <div v-if="failed" class="absolute inset-0 grid place-items-center">
      <Leaf class="size-56 text-lime/70 animate-float" :stroke-width="0.8" />
    </div>
  </div>
</template>
