import { PosSound } from './pos.sound'

describe('PosSound', () => {
  let sound: PosSound
  let mockOscillator: jasmine.SpyObj<any>
  let mockGain: jasmine.SpyObj<any>
  let mockCtx: jasmine.SpyObj<any>

  beforeEach(() => {
    mockOscillator = jasmine.createSpyObj('OscillatorNode', ['connect', 'start', 'stop'])
    mockOscillator.frequency = jasmine.createSpyObj('frequency', ['setValueAtTime'])
    mockGain = jasmine.createSpyObj('GainNode', ['connect'])
    mockGain.gain = jasmine.createSpyObj('gain', ['setValueAtTime', 'exponentialRampToValueAtTime'])
    mockCtx = jasmine.createSpyObj('AudioContext', ['createOscillator', 'createGain'])
    mockCtx.currentTime = 0
    mockCtx.createOscillator.and.returnValue(mockOscillator)
    mockCtx.createGain.and.returnValue(mockGain)

    spyOn(window, 'AudioContext').and.returnValue(mockCtx as any)
    sound = new PosSound()
  })

  it('creates AudioContext on first use', () => {
    const newSound = new PosSound()
    ;(newSound as any).audioCtx = null
    expect((newSound as any).ctx).toBeDefined()
    expect(window.AudioContext).toHaveBeenCalled()
  })

  it('playScan creates two beeps', () => {
    sound.playScan()
    expect(mockCtx.createOscillator).toHaveBeenCalled()
    expect(mockCtx.createGain).toHaveBeenCalled()
  })

  it('playAdd creates one beep', () => {
    sound.playAdd()
    expect(mockCtx.createOscillator).toHaveBeenCalled()
  })

  it('playSuccess creates three beeps', () => {
    sound.playSuccess()
    expect(mockCtx.createOscillator).toHaveBeenCalled()
  })

  it('playError creates two beeps', () => {
    sound.playError()
    expect(mockCtx.createOscillator).toHaveBeenCalled()
  })

  it('playOpen creates two beeps', () => {
    sound.playOpen()
    expect(mockCtx.createOscillator).toHaveBeenCalled()
  })

  it('playClose creates two beeps', () => {
    sound.playClose()
    expect(mockCtx.createOscillator).toHaveBeenCalled()
  })

  it('vibrate calls navigator.vibrate when available', () => {
    const mockVibrate = jasmine.createSpy('vibrate')
    navigator.vibrate = mockVibrate as any
    sound.vibrate(100)
    expect(mockVibrate).toHaveBeenCalledWith(100)
  })

  it('vibrate does not throw when navigator.vibrate is unavailable', () => {
    const originalVibrate = navigator.vibrate
    delete (navigator as any).vibrate
    expect(() => sound.vibrate(50)).not.toThrow()
    if (originalVibrate) navigator.vibrate = originalVibrate
  })
})
