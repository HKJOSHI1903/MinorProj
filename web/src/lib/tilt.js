// v-tilt: the element leans towards the mouse in 3D and a soft light follows the cursor.
// The element reads the CSS variables --rx, --ry (rotation) and --mx, --my (cursor position).
// Usage: <div v-tilt class="tilt">  or  <div v-tilt="6">  (maximum angle in degrees).

const still = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
const touch = () => window.matchMedia('(hover: none)').matches

export const tilt = {
  mounted(el, binding) {
    if (still() || touch()) return
    const max = Number(binding.value) || 9
    let frame = 0

    const move = (event) => {
      const box = el.getBoundingClientRect()
      const x = (event.clientX - box.left) / box.width
      const y = (event.clientY - box.top) / box.height
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        el.style.setProperty('--ry', `${(x - 0.5) * 2 * max}deg`)
        el.style.setProperty('--rx', `${(0.5 - y) * 2 * max}deg`)
        el.style.setProperty('--mx', `${x * 100}%`)
        el.style.setProperty('--my', `${y * 100}%`)
      })
    }
    const leave = () => {
      cancelAnimationFrame(frame)
      el.style.setProperty('--ry', '0deg')
      el.style.setProperty('--rx', '0deg')
    }

    el.addEventListener('pointermove', move)
    el.addEventListener('pointerleave', leave)
    el._tilt = { move, leave }
  },
  unmounted(el) {
    if (!el._tilt) return
    el.removeEventListener('pointermove', el._tilt.move)
    el.removeEventListener('pointerleave', el._tilt.leave)
  },
}
