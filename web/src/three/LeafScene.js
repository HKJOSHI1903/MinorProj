// The 3D hero: a leaf made of thousands of glowing points, with a scan line
// sweeping over it and three "infected" areas pulsing in amber.
//
// It is drawn with Three.js (WebGL). The leaf is one THREE.Points object with a
// small custom shader, so 16,000 points cost a single draw call.

import * as THREE from 'three'

const LEAF_POINTS = 16000
const LENGTH = 3.0 // the leaf runs from y = -1.5 (stem) to y = +1.5 (tip)

// Half-width of the leaf at position u (0 = stem end, 1 = tip).
function halfWidth(u) {
  const clamped = Math.min(Math.max(u, 0), 1)
  return 0.98 * Math.pow(Math.sin(Math.PI * Math.pow(clamped, 0.78)), 0.9) * (1 - 0.22 * clamped)
}

// The leaf is not flat: it is cupped across its width and arches along its length.
function surfaceZ(x, u) {
  return 0.26 * x * x - 0.2 * Math.sin(Math.PI * u) + 0.3 * (u - 0.5) * (u - 0.5)
}

// Centres (x, y) and radii of the infected areas.
const SPOTS = [
  { x: 0.36, y: 0.34, r: 0.21 },
  { x: -0.42, y: -0.3, r: 0.17 },
  { x: 0.14, y: -0.84, r: 0.13 },
]

function buildLeafGeometry() {
  const positions = new Float32Array(LEAF_POINTS * 3)
  const vein = new Float32Array(LEAF_POINTS) // 1 on veins and the outline: drawn brighter
  const spot = new Float32Array(LEAF_POINTS) // 1 inside an infected area: drawn amber
  const random = new Float32Array(LEAF_POINTS)

  for (let i = 0; i < LEAF_POINTS; i++) {
    let u = Math.random()
    let x
    let veinStrength = 0
    const kind = Math.random()

    if (kind < 0.1) {
      // the midrib
      x = (Math.random() - 0.5) * 0.03
      veinStrength = 1
    } else if (kind < 0.36) {
      // side veins: they leave the midrib and run outwards and towards the tip
      const start = 0.08 + Math.floor(Math.random() * 9) * 0.095
      const along = Math.random()
      const side = Math.random() < 0.5 ? -1 : 1
      u = start + along * 0.17
      x = side * along * halfWidth(u) * 0.93 + (Math.random() - 0.5) * 0.02
      veinStrength = 0.75 * (1 - along * 0.5)
    } else if (kind < 0.5) {
      // the outline
      x = (Math.random() < 0.5 ? -1 : 1) * halfWidth(u) * (0.985 + Math.random() * 0.03)
      veinStrength = 0.6
    } else {
      // the leaf surface
      x = (Math.random() * 2 - 1) * halfWidth(u)
    }

    const y = -LENGTH / 2 + LENGTH * u
    const z = surfaceZ(x, u) + (Math.random() - 0.5) * 0.025

    let spotStrength = 0
    for (const s of SPOTS) {
      const distance = Math.hypot(x - s.x, y - s.y)
      spotStrength = Math.max(spotStrength, 1 - THREE.MathUtils.smoothstep(distance, s.r * 0.55, s.r))
    }

    positions.set([x, y, z], i * 3)
    vein[i] = veinStrength
    spot[i] = spotStrength
    random[i] = Math.random()
  }

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('aVein', new THREE.BufferAttribute(vein, 1))
  geometry.setAttribute('aSpot', new THREE.BufferAttribute(spot, 1))
  geometry.setAttribute('aRandom', new THREE.BufferAttribute(random, 1))
  return geometry
}

const leafVertexShader = /* glsl */ `
  attribute float aVein;
  attribute float aSpot;
  attribute float aRandom;
  uniform float uTime;
  uniform float uScan;      // y position of the scan line
  uniform float uHeight;    // canvas height in pixels
  uniform float uIntro;     // 0 -> 1 while the leaf assembles
  varying float vGlow;
  varying float vVein;
  varying float vSpot;
  varying float vRandom;

  void main() {
    vec3 p = position;
    // gentle breathing so the leaf never looks frozen
    p.z += sin(uTime * 1.1 + p.y * 2.2 + aRandom * 6.2831) * 0.014;
    // intro: points fly in from a scattered cloud
    vec3 scattered = p + (vec3(aRandom, fract(aRandom * 7.13), fract(aRandom * 13.7)) - 0.5) * 5.0;
    float arrive = smoothstep(0.0, 1.0, clamp(uIntro * 1.6 - aRandom * 0.6, 0.0, 1.0));
    p = mix(scattered, p, arrive);

    vGlow = smoothstep(0.3, 0.0, abs(position.y - uScan));
    vVein = aVein;
    vSpot = aSpot;
    vRandom = aRandom;

    vec4 viewPosition = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * viewPosition;
    float size = 0.026 * (0.65 + aVein * 0.55 + aSpot * 0.7 + vGlow * 1.3 + aRandom * 0.3);
    gl_PointSize = size * uHeight / -viewPosition.z;
  }
`

const leafFragmentShader = /* glsl */ `
  uniform float uTime;
  varying float vGlow;
  varying float vVein;
  varying float vSpot;
  varying float vRandom;

  void main() {
    float distanceFromCentre = length(gl_PointCoord - 0.5);
    if (distanceFromCentre > 0.5) discard;
    float soft = smoothstep(0.5, 0.05, distanceFromCentre);

    vec3 deep = vec3(0.10, 0.50, 0.26);
    vec3 lime = vec3(0.73, 0.96, 0.32);
    vec3 amber = vec3(1.0, 0.64, 0.22);

    vec3 colour = mix(deep, lime, vVein * 0.85 + vRandom * 0.15);
    float pulse = 0.72 + 0.28 * sin(uTime * 3.0 + vRandom * 6.2831);
    colour = mix(colour, amber, vSpot * pulse);
    colour += vGlow * vec3(0.55, 0.85, 0.45);

    float alpha = soft * (0.42 + vVein * 0.45 + vSpot * 0.4 + vGlow * 0.9);
    gl_FragColor = vec4(colour, alpha);
  }
`

const beamVertexShader = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`

const beamFragmentShader = /* glsl */ `
  varying vec2 vUv;
  void main() {
    float across = pow(1.0 - abs(vUv.y * 2.0 - 1.0), 4.0);     // bright in the middle
    float ends = smoothstep(0.0, 0.18, vUv.x) * smoothstep(1.0, 0.82, vUv.x);
    float line = smoothstep(0.035, 0.0, abs(vUv.y - 0.5));
    gl_FragColor = vec4(vec3(0.73, 0.96, 0.32), (across * 0.2 + line * 0.9) * ends);
  }
`

export function createLeafScene(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.domElement.style.cssText = 'display:block;width:100%;height:100%'
  container.appendChild(renderer.domElement)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 50)
  camera.position.set(0, 0, 6.4)

  // Everything that moves together sits in one group.
  const rig = new THREE.Group()
  scene.add(rig)

  const leafMaterial = new THREE.ShaderMaterial({
    vertexShader: leafVertexShader,
    fragmentShader: leafFragmentShader,
    uniforms: { uTime: { value: 0 }, uScan: { value: 0 }, uHeight: { value: 600 }, uIntro: { value: 0 } },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })
  const leafGeometry = buildLeafGeometry()
  rig.add(new THREE.Points(leafGeometry, leafMaterial))

  // The stem
  const stemPoints = []
  for (let i = 0; i < 60; i++) {
    const k = i / 59
    stemPoints.push(new THREE.Vector3(0.1 * k * k, -LENGTH / 2 - k * 0.75, surfaceZ(0, 0) + 0.1 * k))
  }
  const stemGeometry = new THREE.BufferGeometry().setFromPoints(stemPoints)
  const stemMaterial = new THREE.LineBasicMaterial({ color: 0xb9f551, transparent: true, opacity: 0.7 })
  rig.add(new THREE.Line(stemGeometry, stemMaterial))

  // The scan beam
  const beamMaterial = new THREE.ShaderMaterial({
    vertexShader: beamVertexShader,
    fragmentShader: beamFragmentShader,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  })
  const beamGeometry = new THREE.PlaneGeometry(3.0, 0.7)
  const beam = new THREE.Mesh(beamGeometry, beamMaterial)
  beam.position.z = 0.12
  rig.add(beam)

  // Rings around the infected areas
  const rings = SPOTS.map((s) => {
    const geometry = new THREE.RingGeometry(s.r * 1.12, s.r * 1.12 + 0.012, 64)
    const material = new THREE.MeshBasicMaterial({
      color: 0xffb547,
      transparent: true,
      opacity: 0,
      side: THREE.DoubleSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
    const ring = new THREE.Mesh(geometry, material)
    ring.position.set(s.x, s.y, surfaceZ(s.x, (s.y + LENGTH / 2) / LENGTH) + 0.09)
    rig.add(ring)
    return ring
  })

  // Dust in the air around the leaf
  const dustCount = 420
  const dustPositions = new Float32Array(dustCount * 3)
  for (let i = 0; i < dustCount; i++) {
    dustPositions.set(
      [(Math.random() - 0.5) * 9, (Math.random() - 0.5) * 7, (Math.random() - 0.5) * 5 - 0.5],
      i * 3,
    )
  }
  const dustGeometry = new THREE.BufferGeometry()
  dustGeometry.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3))
  const dustMaterial = new THREE.PointsMaterial({
    color: 0xb9f551,
    size: 0.022,
    transparent: true,
    opacity: 0.4,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })
  const dust = new THREE.Points(dustGeometry, dustMaterial)
  scene.add(dust)

  rig.rotation.set(-0.5, 0.3, -0.32)

  // ----- sizing -----
  function resize() {
    const width = container.clientWidth
    const height = container.clientHeight
    if (!width || !height) return
    renderer.setSize(width, height, false)
    camera.aspect = width / height
    // keep the whole leaf in view on tall, narrow screens
    camera.position.z = camera.aspect < 0.8 ? 6.4 / Math.max(camera.aspect, 0.5) * 0.82 : 6.4
    camera.updateProjectionMatrix()
    leafMaterial.uniforms.uHeight.value = height * renderer.getPixelRatio()
  }
  const resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(container)
  resize()

  // ----- pointer parallax -----
  const pointer = { x: 0, y: 0 }
  const eased = { x: 0, y: 0 }
  function onPointerMove(event) {
    pointer.x = (event.clientX / window.innerWidth) * 2 - 1
    pointer.y = (event.clientY / window.innerHeight) * 2 - 1
  }
  window.addEventListener('pointermove', onPointerMove, { passive: true })

  // ----- animation loop -----
  const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const clock = new THREE.Clock()
  let frame = 0
  let visible = true
  let disposed = false

  function render() {
    const time = still ? 2.2 : clock.getElapsedTime()
    const scanY = Math.sin(time * 0.75) * 1.7

    leafMaterial.uniforms.uTime.value = time
    leafMaterial.uniforms.uScan.value = scanY
    leafMaterial.uniforms.uIntro.value = still ? 1 : Math.min(time / 2.2, 1)
    beam.position.y = scanY

    // a ring lights up as the scan line passes its spot, then fades
    rings.forEach((ring, index) => {
      const near = 1 - Math.min(Math.abs(scanY - SPOTS[index].y) / 0.9, 1)
      ring.material.opacity = 0.25 + near * 0.75
      ring.scale.setScalar(1 + near * 0.12 + Math.sin(time * 2.5 + index) * 0.03)
    })

    eased.x += (pointer.x - eased.x) * 0.05
    eased.y += (pointer.y - eased.y) * 0.05
    rig.rotation.y = 0.3 + Math.sin(time * 0.32) * 0.42 + eased.x * 0.45
    rig.rotation.x = -0.5 + Math.sin(time * 0.24) * 0.08 + eased.y * 0.2
    rig.position.y = Math.sin(time * 0.8) * 0.07
    dust.rotation.y = time * 0.02
    dust.position.y = Math.sin(time * 0.2) * 0.15

    renderer.render(scene, camera)
  }

  function loop() {
    if (disposed) return
    if (visible) render()
    if (!still) frame = requestAnimationFrame(loop)
  }
  loop()

  // Stop drawing while the hero is scrolled out of view.
  const visibilityObserver = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting
  })
  visibilityObserver.observe(container)

  return {
    dispose() {
      disposed = true
      cancelAnimationFrame(frame)
      window.removeEventListener('pointermove', onPointerMove)
      resizeObserver.disconnect()
      visibilityObserver.disconnect()
      ;[leafGeometry, stemGeometry, beamGeometry, dustGeometry].forEach((g) => g.dispose())
      ;[leafMaterial, stemMaterial, beamMaterial, dustMaterial].forEach((m) => m.dispose())
      rings.forEach((ring) => {
        ring.geometry.dispose()
        ring.material.dispose()
      })
      renderer.dispose()
      renderer.domElement.remove()
    },
  }
}
