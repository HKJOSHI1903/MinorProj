// v-reveal: the element fades and rises into place the first time it is scrolled into view.
// Usage: <div v-reveal>  or  <div v-reveal="120">  (delay in milliseconds).

let observer

function getObserver() {
  if (!observer) {
    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            observer.unobserve(entry.target)
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )
  }
  return observer
}

export const reveal = {
  mounted(el, binding) {
    el.classList.add('reveal')
    if (binding.value) el.style.transitionDelay = `${binding.value}ms`
    if (!('IntersectionObserver' in window)) {
      el.classList.add('is-visible')
      return
    }
    getObserver().observe(el)
  },
  unmounted(el) {
    observer?.unobserve(el)
  },
}
