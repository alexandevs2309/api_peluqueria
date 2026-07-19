import { Injectable } from '@angular/core'

@Injectable({ providedIn: 'root' })
export class PosSound {
  private audioCtx: AudioContext | null = null

  private get ctx(): AudioContext {
    if (!this.audioCtx) {
      this.audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
    }
    return this.audioCtx
  }

  private beep(freq: number, duration: number, start: number, volume = 0.3) {
    const osc = this.ctx.createOscillator()
    const gain = this.ctx.createGain()
    osc.connect(gain)
    gain.connect(this.ctx.destination)
    osc.frequency.setValueAtTime(freq, start)
    gain.gain.setValueAtTime(volume, start)
    gain.gain.exponentialRampToValueAtTime(0.01, start + duration)
    osc.start(start)
    osc.stop(start + duration)
  }

  playScan() {
    const t = this.ctx.currentTime
    this.beep(1200, 0.08, t, 0.2)
    this.beep(1500, 0.06, t + 0.06, 0.2)
  }

  playAdd() {
    const t = this.ctx.currentTime
    this.beep(600, 0.1, t, 0.15)
  }

  playSuccess() {
    const t = this.ctx.currentTime
    this.beep(800, 0.15, t)
    this.beep(1000, 0.15, t + 0.1)
    this.beep(1200, 0.2, t + 0.2)
  }

  playError() {
    const t = this.ctx.currentTime
    this.beep(300, 0.2, t, 0.4)
    this.beep(200, 0.3, t + 0.15, 0.4)
  }

  playOpen() {
    const t = this.ctx.currentTime
    this.beep(500, 0.15, t, 0.2)
    this.beep(700, 0.15, t + 0.12, 0.2)
  }

  playClose() {
    const t = this.ctx.currentTime
    this.beep(400, 0.2, t, 0.2)
    this.beep(300, 0.25, t + 0.15, 0.2)
  }

  vibrate(pattern: number | number[] = 50) {
    if (navigator.vibrate) navigator.vibrate(pattern)
  }
}
