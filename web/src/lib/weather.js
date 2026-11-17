// Local weather from Open-Meteo (free, no account or key). The browser asks the
// farmer for their location and sends only the coordinates to Open-Meteo.

const RAIN_WINDOW_HOURS = 12
const MAX_WIND_KMH = 15
const MAX_RAIN_CHANCE = 30

function locate() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('unsupported'))
    navigator.geolocation.getCurrentPosition(
      (position) => resolve(position.coords),
      (error) => reject(new Error(error.code === 1 ? 'denied' : 'unavailable')),
      { timeout: 12000, maximumAge: 10 * 60 * 1000 },
    )
  })
}

// Returns { temperature, humidity, wind, rainChance, sprayOk, reason }.
// Throws an Error whose message is 'denied', 'unsupported', 'unavailable' or 'network'.
export async function getWeather() {
  const { latitude, longitude } = await locate()
  const url =
    'https://api.open-meteo.com/v1/forecast' +
    `?latitude=${latitude.toFixed(3)}&longitude=${longitude.toFixed(3)}` +
    '&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation' +
    '&hourly=precipitation_probability&forecast_days=2&timezone=auto'

  let data
  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error('network')
    data = await response.json()
  } catch {
    throw new Error('network')
  }

  // Highest chance of rain in the next 12 hours.
  const now = data.current.time.slice(0, 13) // "2026-11-17T09"
  const start = Math.max(data.hourly.time.findIndex((time) => time.slice(0, 13) === now), 0)
  const chances = data.hourly.precipitation_probability.slice(start, start + RAIN_WINDOW_HOURS)
  const rainChance = Math.max(0, ...chances.filter((value) => typeof value === 'number'))

  const wind = data.current.wind_speed_10m
  const raining = data.current.precipitation > 0
  // A simple rule of thumb: spray lasts only if it stays dry and the air is calm.
  let reason = 'ok'
  if (raining) reason = 'raining'
  else if (rainChance > MAX_RAIN_CHANCE) reason = 'rain'
  else if (wind > MAX_WIND_KMH) reason = 'wind'

  return {
    temperature: data.current.temperature_2m,
    humidity: data.current.relative_humidity_2m,
    wind,
    rainChance,
    sprayOk: reason === 'ok',
    reason,
  }
}
