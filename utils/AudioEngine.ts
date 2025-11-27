const FADE_OUT_DURATION = 0.015; // 15ms
const FADE_CURVE_SAMPLES = 128;

interface ActiveSource {
    source: AudioBufferSourceNode;
    gain: GainNode;
}

export class AudioEngineWithFade {
    private context: AudioContext;
    private masterGain: GainNode;
    private activeSources: Map<string, ActiveSource> = new Map();
    private fadeOutCurve: Float32Array;
    private samplesPlayed: number = 0;
    
    constructor() {
        this.context = new (window.AudioContext || (window as any).webkitAudioContext)();
        this.masterGain = this.context.createGain();
        this.masterGain.connect(this.context.destination);
        this.fadeOutCurve = this.createFadeCurve(FADE_CURVE_SAMPLES);
    }
    
    private createFadeCurve(length: number): Float32Array {
        const curve = new Float32Array(length);
        for (let i = 0; i < length; i++) {
            // Equal-power fade: cos(x * π/2)
            const x = i / (length - 1);
            curve[i] = Math.cos(x * Math.PI * 0.5);
        }
        return curve;
    }
    
    async resume(): Promise<void> {
        if (this.context.state === 'suspended') {
            await this.context.resume();
        }
    }
    
    async playAudio(base64Audio: string): Promise<void> {
        await this.resume();
        
        const binaryString = window.atob(base64Audio);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        
        // Convert PCM16 to Float32
        const int16Array = new Int16Array(bytes.buffer);
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }
        
        const audioBuffer = this.context.createBuffer(1, float32Array.length, 24000);
        audioBuffer.getChannelData(0).set(float32Array);
        
        const chunkId = Math.random().toString(36).substring(7);
        this.playChunk(audioBuffer, chunkId);
    }

    playChunk(audioBuffer: AudioBuffer, chunkId: string): void {
        const source = this.context.createBufferSource();
        const gainNode = this.context.createGain();
        
        source.buffer = audioBuffer;
        source.connect(gainNode);
        gainNode.connect(this.masterGain);
        
        this.activeSources.set(chunkId, { source, gain: gainNode });
        
        source.onended = () => {
            this.activeSources.delete(chunkId);
        };
        
        source.start();
        this.samplesPlayed += audioBuffer.length;
    }
    
    /**
     * Gracefully stop all audio with anti-click fade
     * THE KEY FIX for barge-in artifacts
     */
    async stopAllWithFade(): Promise<void> {
        return new Promise((resolve) => {
            const now = this.context.currentTime;
            
            console.log(`[AudioEngine] 🛑 Fading ${this.activeSources.size} sources over ${FADE_OUT_DURATION * 1000}ms`);
            
            if (this.activeSources.size === 0) {
                resolve();
                return;
            }
            
            for (const [id, { source, gain }] of this.activeSources) {
                try {
                    gain.gain.cancelScheduledValues(now);
                    gain.gain.setValueAtTime(gain.gain.value, now);
                    gain.gain.setValueCurveAtTime(this.fadeOutCurve, now, FADE_OUT_DURATION);
                    source.stop(now + FADE_OUT_DURATION + 0.001);
                } catch (e) {
                    console.warn(`[AudioEngine] Error stopping source ${id}:`, e);
                }
            }
            
            setTimeout(() => {
                for (const [id, { source }] of this.activeSources) {
                    try { source.disconnect(); } catch (e) {}
                }
                this.activeSources.clear();
                resolve();
            }, FADE_OUT_DURATION * 1000 + 10);
        });
    }
    
    stopAllImmediate(): void {
        for (const [id, { source, gain }] of this.activeSources) {
            try {
                gain.gain.setValueAtTime(0, this.context.currentTime);
                source.stop();
                source.disconnect();
            } catch (e) {}
        }
        this.activeSources.clear();
    }
    
    getPlaybackPositionMs(): number {
        return Math.floor((this.samplesPlayed / 24000) * 1000); // 24kHz sample rate
    }
}

export const audioEngine = new AudioEngineWithFade();
