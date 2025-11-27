/**
 * useVoiceRecorder - Audio capture hook for voice interface
 * Captures microphone audio at 24kHz, converts to PCM16 base64
 */

import { useRef, useState, useCallback } from 'react';

interface UseVoiceRecorderReturn {
  isRecording: boolean;
  micLevel: number;
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  setOnAudioData: (callback: (base64Audio: string) => void) => void;
}

export function useVoiceRecorder(): UseVoiceRecorderReturn {
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const callbackRef = useRef<((base64Audio: string) => void) | null>(null);
  
  const [isRecording, setIsRecording] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  const setOnAudioData = useCallback((callback: (base64Audio: string) => void) => {
    callbackRef.current = callback;
  }, []);

  const startRecording = useCallback(async () => {
    try {
      setError(null);
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 24000
        }
      });
      
      // Create AudioContext at 24kHz (OpenAI Realtime requirement)
      const audioContext = new AudioContext({ sampleRate: 24000 });
      
      // Create source and processor
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      
      // Process audio chunks
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Calculate RMS for level meter
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        setMicLevel(Math.min(1, rms * 10)); // Scale for visibility
        
        // Convert Float32 to PCM16
        const pcm16 = float32ToInt16(inputData);
        
        // Convert to base64 (cast to ArrayBuffer for TypeScript)
        const base64 = arrayBufferToBase64(pcm16.buffer as ArrayBuffer);
        
        // Emit to callback
        if (callbackRef.current) {
          callbackRef.current(base64);
        }
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      streamRef.current = stream;
      audioContextRef.current = audioContext;
      processorRef.current = processor;
      setIsRecording(true);
      
    } catch (err: any) {
      console.error('Microphone access error:', err);
      setError(err.message || 'Failed to access microphone');
    }
  }, []);

  const stopRecording = useCallback(() => {
    // Stop all tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    // Disconnect processor
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    
    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    setIsRecording(false);
    setMicLevel(0);
  }, []);

  return {
    isRecording,
    micLevel,
    error,
    startRecording,
    stopRecording,
    setOnAudioData
  };
}

// Convert Float32Array to Int16Array (PCM16)
function float32ToInt16(float32Array: Float32Array): Int16Array {
  const int16 = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return int16;
}

// Convert ArrayBuffer to base64
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export default useVoiceRecorder;
