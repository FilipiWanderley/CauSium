export const NOTIFICATIONS_SOUND_ENABLED_KEY = 'sp.notifications.sound.enabled'

export function isNotificationSoundEnabled(): boolean {
  try {
    const value = window.localStorage.getItem(NOTIFICATIONS_SOUND_ENABLED_KEY)
    if (value === null) return true
    return value === '1'
  } catch {
    return true
  }
}

export function setNotificationSoundEnabled(enabled: boolean): void {
  try {
    window.localStorage.setItem(NOTIFICATIONS_SOUND_ENABLED_KEY, enabled ? '1' : '0')
  } catch {
    // Ignore storage errors (private mode/quota).
  }
}

export function playCriticalNotificationSound(): void {
  if (!isNotificationSoundEnabled()) return
  if (typeof window === 'undefined') return
  const AudioCtx =
    window.AudioContext ||
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).webkitAudioContext
  if (!AudioCtx) return

  try {
    const ctx = new AudioCtx()
    const now = ctx.currentTime

    const beep = (offset: number, frequency: number, duration: number) => {
      const oscillator = ctx.createOscillator()
      const gain = ctx.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.value = frequency
      gain.gain.setValueAtTime(0.0001, now + offset)
      gain.gain.exponentialRampToValueAtTime(0.08, now + offset + 0.01)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + duration)
      oscillator.connect(gain)
      gain.connect(ctx.destination)
      oscillator.start(now + offset)
      oscillator.stop(now + offset + duration + 0.02)
    }

    beep(0, 920, 0.14)
    beep(0.2, 740, 0.16)
    window.setTimeout(() => {
      void ctx.close()
    }, 700)
  } catch {
    // Ignore playback errors (autoplay policy, etc.).
  }
}
