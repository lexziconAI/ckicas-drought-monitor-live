/**
 * useVoiceWebSocket - WebSocket connection to voice relay
 * Handles bidirectional audio streaming with OpenAI Realtime API
 */

import { useRef, useState, useCallback, useEffect } from 'react';

interface VoiceWebSocketReturn {
  isConnected: boolean;
  error: string | null;
  isSpeaking: 'user' | 'ai' | 'none';
  connect: () => void;
  disconnect: () => void;
  sendAudio: (base64Audio: string) => void;
  setOnTranscription: (callback: (text: string, role: 'user' | 'assistant') => void) => void;
  setOnAudioOutput: (callback: (base64Audio: string) => void) => void;
  setOnBargeIn: (callback: () => void) => void;
  setOnFractalUpdate: (callback: (tree: any, path: string[]) => void) => void;
}

// Determine the WebSocket URL based on the environment
const getVoiceRelayUrl = () => {
  // 1. Prefer environment variable if set
  if (import.meta.env.VITE_VOICE_RELAY_URL) {
    return import.meta.env.VITE_VOICE_RELAY_URL;
  }

  // 2. If running on localhost, default to local backend port 9101
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'ws://localhost:9101/api/ws/voice-relay';
  }

  // 3. In production, use VITE_API_BASE_URL if available
  if (import.meta.env.VITE_API_BASE_URL) {
    const baseUrl = import.meta.env.VITE_API_BASE_URL;
    // Replace http/https with ws/wss
    const wsUrl = baseUrl.replace(/^http/, 'ws');
    return `${wsUrl}/api/ws/voice-relay`;
  }

  // 4. Fallback to current host (only works if served from same origin)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/ws/voice-relay`;
};

const VOICE_RELAY_URL = getVoiceRelayUrl();

export function useVoiceWebSocket(): VoiceWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const transcriptionCallbackRef = useRef<((text: string, role: 'user' | 'assistant') => void) | null>(null);
  const audioOutputCallbackRef = useRef<((base64Audio: string) => void) | null>(null);
  const bargeInCallbackRef = useRef<(() => void) | null>(null);
  const fractalUpdateCallbackRef = useRef<((tree: any, path: string[]) => void) | null>(null);
  
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState<'user' | 'ai' | 'none'>('none');

  const setOnTranscription = useCallback((callback: (text: string, role: 'user' | 'assistant') => void) => {
    transcriptionCallbackRef.current = callback;
  }, []);

  const setOnAudioOutput = useCallback((callback: (base64Audio: string) => void) => {
    audioOutputCallbackRef.current = callback;
  }, []);

  const setOnBargeIn = useCallback((callback: () => void) => {
    bargeInCallbackRef.current = callback;
  }, []);

  const setOnFractalUpdate = useCallback((callback: (tree: any, path: string[]) => void) => {
    fractalUpdateCallbackRef.current = callback;
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setError(null);
    console.log('[Voice] Connecting to:', VOICE_RELAY_URL);
    
    const ws = new WebSocket(VOICE_RELAY_URL);
    
    ws.onopen = () => {
      console.log('[Voice] Connected to voice relay');
      setIsConnected(true);
      setError(null);
    };
    
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        
        switch (msg.type) {
          // Fractal Engine Events
          case 'fractal.thought_update':
            if (fractalUpdateCallbackRef.current) {
              fractalUpdateCallbackRef.current(msg.tree, msg.path);
            }
            break;

          // Session events
          case 'session.created':
            console.log('[Voice] Session created:', msg.session?.id);
            break;
            
          // Heartbeat
          case 'heartbeat_ping':
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({
                type: 'heartbeat_pong',
                timestamp: msg.timestamp,
                clientTime: Date.now()
              }));
            }
            break;
            
          case 'session.updated':
            console.log('[Voice] Session updated');
            break;
            
          // Input audio events
          case 'input_audio_buffer.speech_started':
            console.log('[Voice] 🛑 BARGE-IN: User started speaking');
            setIsSpeaking('user');
            // CRITICAL: Trigger barge-in callback to stop audio playback immediately
            if (bargeInCallbackRef.current) {
              bargeInCallbackRef.current();
            }
            break;
            
          case 'input_audio_buffer.speech_stopped':
            setIsSpeaking('none');
            break;
            
          // Transcription events
          case 'conversation.item.input_audio_transcription.completed':
            if (msg.transcript && transcriptionCallbackRef.current) {
              transcriptionCallbackRef.current(msg.transcript, 'user');
            }
            break;
            
          case 'response.audio_transcript.done':
            if (msg.transcript && transcriptionCallbackRef.current) {
              transcriptionCallbackRef.current(msg.transcript, 'assistant');
            }
            break;
            
          // Audio output events
          case 'response.audio.delta':
            setIsSpeaking('ai');
            if (msg.delta && audioOutputCallbackRef.current) {
              audioOutputCallbackRef.current(msg.delta);
            }
            break;
            
          case 'response.audio.done':
            setIsSpeaking('none');
            break;
            
          // Response events
          case 'response.done':
            setIsSpeaking('none');
            break;
            
          // Error events
          case 'error':
            console.error('[Voice] Error from server:', msg.error);
            setError(msg.error?.message || 'Unknown error');
            break;
            
          // Tool calls (for debugging)
          case 'response.function_call_arguments.done':
            console.log('[Voice] Tool call:', msg.name);
            break;
        }
      } catch (err) {
        console.error('[Voice] Error parsing message:', err);
      }
    };
    
    ws.onerror = (err) => {
      console.error('[Voice] WebSocket error:', err);
      setError('Connection failed');
    };
    
    ws.onclose = (event) => {
      console.log('[Voice] WebSocket closed:', event.code, event.reason);
      setIsConnected(false);
      setIsSpeaking('none');
      
      // Don't set error for normal closure
      if (event.code !== 1000) {
        setError(`Connection closed: ${event.reason || 'Unknown reason'}`);
      }
    };
    
    wsRef.current = ws;
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
    setIsConnected(false);
    setIsSpeaking('none');
  }, []);

  const sendAudio = useCallback((base64Audio: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'input_audio_buffer.append',
        audio: base64Audio
      }));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isConnected,
    error,
    isSpeaking,
    connect,
    disconnect,
    sendAudio,
    setOnTranscription,
    setOnAudioOutput,
    setOnBargeIn,
    setOnFractalUpdate
  };
}

export default useVoiceWebSocket;
