/**
 * VoiceControlPanel - Kaitiaki Wai Voice Assistant UI
 * Real-time voice interface to CKICAS Drought Monitor
 * Uses OpenAI Realtime API (gpt-4o-mini-realtime-preview-2024-12-17)
 */

import { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Phone, PhoneOff, Volume2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import { useVoiceWebSocket } from '../hooks/useVoiceWebSocket';
import { audioEngine } from '../utils/AudioEngine';

interface TranscriptItem {
  role: 'user' | 'assistant';
  text: string;
  timestamp: Date;
}

interface VoiceControlPanelProps {
  onClose?: () => void;
}

export default function VoiceControlPanel({ onClose: _onClose }: VoiceControlPanelProps) {
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [isMuted, setIsMuted] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Voice recorder hook
  const { 
    isRecording, 
    micLevel, 
    error: recorderError, 
    startRecording, 
    stopRecording,
    setOnAudioData 
  } = useVoiceRecorder();

  // WebSocket hook
  const {
    isConnected,
    error: wsError,
    isSpeaking,
    connect,
    disconnect,
    sendAudio,
    setOnTranscription,
    setOnAudioOutput,
    setOnBargeIn
  } = useVoiceWebSocket();

  // Setup audio data callback
  useEffect(() => {
    setOnAudioData((base64Audio) => {
      if (!isMuted && isConnected) {
        sendAudio(base64Audio);
      }
    });
  }, [setOnAudioData, sendAudio, isMuted, isConnected]);

  // Setup transcription callback
  useEffect(() => {
    setOnTranscription((text, role) => {
      setTranscript(prev => [...prev, {
        role,
        text,
        timestamp: new Date()
      }]);
    });
  }, [setOnTranscription]);

  // Setup audio output callback
  useEffect(() => {
    setOnAudioOutput((base64Audio) => {
      audioEngine.playAudio(base64Audio);
    });
  }, [setOnAudioOutput]);

  // Setup barge-in callback - CRITICAL: Stop audio immediately when user speaks
  useEffect(() => {
    setOnBargeIn(async () => {
      console.log('[VoicePanel] 🛑 BARGE-IN: Stopping all audio playback');
      await audioEngine.stopAllWithFade();
    });
  }, [setOnBargeIn]);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  // Session timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isConnected) {
      interval = setInterval(() => {
        setSessionTime(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isConnected]);

  // Start session
  const startSession = async () => {
    setTranscript([]);
    setSessionTime(0);
    connect();
    await startRecording();
  };

  // End session
  const endSession = () => {
    stopRecording();
    disconnect();
    audioEngine.stopAllWithFade();
  };

  // Toggle mute
  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (!isMuted) {
      // Stopping audio - barge-in
      audioEngine.stopAllWithFade();
    }
  };

  // Format time
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const error = recorderError || wsError;

  return (
    <div className="bg-slate-900/95 backdrop-blur-sm rounded-xl border border-slate-700 shadow-2xl overflow-hidden w-full max-w-md">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-900/50 to-cyan-900/50 p-4 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600/30 rounded-lg">
              <Volume2 className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h3 className="font-bold text-white text-lg">Kaitiaki Wai</h3>
              <p className="text-xs text-slate-400">Drought Monitor Voice Assistant</p>
            </div>
          </div>
          {isConnected && (
            <div className="flex items-center gap-2 text-emerald-400">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-sm font-mono">{formatTime(sessionTime)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Visualizer */}
      <div className="p-4 bg-slate-950/50">
        <div className="relative h-24 bg-slate-900 rounded-lg overflow-hidden border border-slate-800">
          {/* AI Waveform (top) */}
          <div className="absolute top-0 left-0 right-0 h-1/2 flex items-center justify-center border-b border-slate-800/50">
            <div className="flex items-center gap-0.5">
              {Array.from({ length: 32 }).map((_, i) => (
                <motion.div
                  key={`ai-${i}`}
                  className="w-1 bg-blue-500 rounded-full"
                  animate={{
                    height: isSpeaking === 'ai' 
                      ? Math.random() * 30 + 4 
                      : 4
                  }}
                  transition={{ duration: 0.1 }}
                />
              ))}
            </div>
            <span className="absolute left-2 top-1 text-[10px] text-blue-400 font-mono">AI</span>
          </div>

          {/* User Waveform (bottom) */}
          <div className="absolute bottom-0 left-0 right-0 h-1/2 flex items-center justify-center">
            <div className="flex items-center gap-0.5">
              {Array.from({ length: 32 }).map((_, i) => (
                <motion.div
                  key={`user-${i}`}
                  className="w-1 bg-emerald-500 rounded-full"
                  animate={{
                    height: isRecording && !isMuted
                      ? micLevel * 60 * (0.5 + Math.random() * 0.5) + 4
                      : 4
                  }}
                  transition={{ duration: 0.05 }}
                />
              ))}
            </div>
            <span className="absolute left-2 bottom-1 text-[10px] text-emerald-400 font-mono">YOU</span>
          </div>

          {/* Connection status overlay */}
          {!isConnected && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/80">
              <span className="text-slate-400 text-sm">Click Start to begin</span>
            </div>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="p-4 flex items-center justify-center gap-4">
        {!isConnected ? (
          <button
            onClick={startSession}
            className="flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-full font-semibold transition-colors shadow-lg shadow-emerald-900/50"
          >
            <Phone className="w-5 h-5" />
            Start Session
          </button>
        ) : (
          <>
            <button
              onClick={toggleMute}
              className={`p-3 rounded-full transition-colors ${
                isMuted 
                  ? 'bg-amber-600 hover:bg-amber-500' 
                  : 'bg-slate-700 hover:bg-slate-600'
              }`}
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? (
                <MicOff className="w-5 h-5 text-white" />
              ) : (
                <Mic className="w-5 h-5 text-white" />
              )}
            </button>
            
            <button
              onClick={endSession}
              className="flex items-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-500 text-white rounded-full font-semibold transition-colors shadow-lg shadow-red-900/50"
            >
              <PhoneOff className="w-5 h-5" />
              End Session
            </button>
          </>
        )}
      </div>

      {/* Transcript */}
      <div className="border-t border-slate-700">
        <div className="p-2 bg-slate-800/50 border-b border-slate-700">
          <span className="text-xs text-slate-400 font-medium">Transcript</span>
        </div>
        <div className="h-48 overflow-y-auto p-3 space-y-2">
          <AnimatePresence>
            {transcript.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${
                    item.role === 'user'
                      ? 'bg-emerald-600/30 text-emerald-100 rounded-br-none'
                      : 'bg-blue-600/30 text-blue-100 rounded-bl-none'
                  }`}
                >
                  {item.text}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {transcript.length === 0 && (
            <div className="text-center text-slate-500 text-sm py-8">
              Conversation will appear here...
            </div>
          )}
          
          <div ref={transcriptEndRef} />
        </div>
      </div>

      {/* Error display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-red-900/50 bg-red-950/30 p-3"
          >
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer */}
      <div className="p-2 bg-slate-800/30 border-t border-slate-700 text-center">
        <span className="text-[10px] text-slate-500">
          Powered by OpenAI Realtime • gpt-4o-mini-realtime-preview
        </span>
      </div>
    </div>
  );
}
