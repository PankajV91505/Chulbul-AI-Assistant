/**
 * App.jsx — Root component for Chulbul AI frontend.
 */

import { useState, useRef, useEffect, useCallback } from 'react';

import Header from './components/Header';
import VoiceOrb3D from './components/VoiceOrb3D';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';

import { useVoiceRecorder } from './hooks/useVoiceRecorder';
import { useAudioAnalyser } from './hooks/useAudioAnalyser';
import { useWakeWord } from './hooks/useWakeWord';
import { transcribeAudio, generateTTS, streamMessage, getAudioUrl } from './api';

const SILENCE_THRESHOLD = 5; // Amplitude out of 255
const SILENCE_DURATION_MS = 4000; // 4 seconds of silence stops recording

export default function App() {
  // ── State ──
  const [messages, setMessages] = useState([]);
  const [language, setLanguage] = useState('en');
  const [sessionId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [greetingPlayed, setGreetingPlayed] = useState(false);
  const [toolStatus, setToolStatus] = useState('');

  // ── Hooks ──
  const { isRecording, startRecording, stopRecording, stream: micStream } = useVoiceRecorder();
  const { frequencyData, connect, disconnect } = useAudioAnalyser();

  // ── Refs ──
  const chatEndRef = useRef(null);
  const audioRef = useRef(null);
  const silenceStartRef = useRef(null);
  const silenceIntervalRef = useRef(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, toolStatus]);

  // ── Helpers ──
  const addMessage = useCallback((role, text, toolUsed = 'direct_response', id = Date.now()) => {
    setMessages((prev) => [...prev, { id, role, text, toolUsed }]);
    return id;
  }, []);

  const updateMessage = useCallback((id, textChunk) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === id ? { ...msg, text: msg.text + textChunk } : msg
      )
    );
  }, []);

  const playGreeting = useCallback(() => {
    if (greetingPlayed) return;
    setGreetingPlayed(true);
    
    // Play greeting instantly using native browser TTS
    try {
      const text = language === 'en' 
        ? "Hello! I am Chulbul, your AI assistant. How can I help you?" 
        : "Namaste! Main Chulbul hoon. Main aapki kaise madad kar sakti hoon?";
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = language === 'en' ? 'en-US' : 'hi-IN';
      utterance.pitch = 1.1; // Slightly higher pitch for a friendly voice
      window.speechSynthesis.speak(utterance);
      
      // Also add a welcome message to the chat
      addMessage('assistant', text, 'direct_response', Date.now());
    } catch (e) {
      console.error("Speech synthesis failed", e);
    }
  }, [greetingPlayed, language, addMessage]);

  const playAudioUrl = useCallback((audioUrl) => {
    if (!audioUrl) return;
    const fullUrl = getAudioUrl(audioUrl);
    if (!fullUrl) return;

    const audio = new Audio(fullUrl);
    audioRef.current = audio;

    audio.addEventListener('canplaythrough', () => {
      audio.play().catch(() => {});
      try { connect(audio); } catch {}
    });

    audio.addEventListener('ended', () => {
      disconnect();
    });
  }, [connect, disconnect]);

  // ── Streaming Chat Handler ──
  const handleStreamingChat = useCallback(async (userText) => {
    setIsLoading(true);
    setToolStatus('');
    const assistantMsgId = addMessage('assistant', '');

    let fullAssistantText = '';

    await streamMessage(userText, language, {
      onChunk: (chunk) => {
        updateMessage(assistantMsgId, chunk);
        fullAssistantText += chunk;
      },
      onTool: (toolName) => {
        setToolStatus(`Executing tool: ${toolName}...`);
      },
      onDone: async () => {
        setIsLoading(false);
        setToolStatus('');
        // Generate TTS for the final text asynchronously
        if (fullAssistantText.trim()) {
          try {
            const ttsRes = await generateTTS(fullAssistantText, language);
            if (ttsRes.audio_url) {
              playAudioUrl(ttsRes.audio_url);
            }
          } catch (e) {
            console.error("TTS Error:", e);
          }
        }
      },
      onError: (err) => {
        setIsLoading(false);
        setToolStatus('');
        updateMessage(assistantMsgId, `\n\n[Error: ${err.message}]`);
      }
    });
  }, [language, addMessage, updateMessage, playAudioUrl]);

  const handleSend = useCallback(async (text) => {
    if (!greetingPlayed) setGreetingPlayed(true);
    addMessage('user', text);
    await handleStreamingChat(text);
  }, [greetingPlayed, addMessage, handleStreamingChat]);

  // ── Voice & Silence Detection ──
  const handleMicToggle = useCallback(async (forceStart = false) => {
    if (!greetingPlayed) setGreetingPlayed(true);
    if (isRecording && !forceStart) {
      // Manual stop
      const blob = await stopRecording();
      if (silenceIntervalRef.current) clearInterval(silenceIntervalRef.current);
      if (!blob) return;
      
      processAudioBlob(blob);
    } else if (!isRecording) {
      // Start recording
      await startRecording();
    }
  }, [greetingPlayed, isRecording, startRecording, stopRecording]);

  const processAudioBlob = async (blob) => {
    const tempMsgId = addMessage('user', '🎤 [Transcribing...]');
    setIsLoading(true);

    try {
      // Fast transcription
      const res = await transcribeAudio(blob, language);
      // Replace transcription text
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempMsgId ? { ...msg, text: res.text } : msg
        )
      );
      // Start streaming response
      await handleStreamingChat(res.text);
    } catch (err) {
      setIsLoading(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempMsgId ? { ...msg, text: `🎤 [Error: ${err.message}]` } : msg
        )
      );
    }
  };

  // ── Silence Detection ──
  const SILENCE_THRESHOLD = 0.15; // 0..1 scale (increased to tolerate background noise)
  const SILENCE_DURATION_MS = 2500; // Auto-stop after 2.5s of silence

  useEffect(() => {
    if (isRecording && micStream) {
      connect(micStream);
      silenceIntervalRef.current = setInterval(() => {
        if (!frequencyData) return;
        
        // Calculate average volume
        const sum = frequencyData.reduce((a, b) => a + b, 0);
        const avg = sum / frequencyData.length;

        // Uncomment for debugging: console.log("Mic volume avg:", avg.toFixed(3));

        if (avg < SILENCE_THRESHOLD) {
          // Silence detected
          if (!silenceStartRef.current) {
            silenceStartRef.current = Date.now();
          } else if (Date.now() - silenceStartRef.current > SILENCE_DURATION_MS) {
            // Silence detected for 2.5 seconds! Auto-stop.
            console.log("Silence detected! Stopping recording...");
            clearInterval(silenceIntervalRef.current);
            stopRecording().then((blob) => {
              if (blob) processAudioBlob(blob);
            });
          }
        } else {
          // Voice detected, reset silence timer
          silenceStartRef.current = null;
        }
      }, 200);
    } else {
      if (silenceIntervalRef.current) clearInterval(silenceIntervalRef.current);
    }

    return () => {
      if (silenceIntervalRef.current) clearInterval(silenceIntervalRef.current);
    };
  }, [isRecording, micStream, frequencyData, connect, stopRecording]);

  // ── Wake Word Detection ──
  useWakeWord(() => {
    if (!greetingPlayed) setGreetingPlayed(true);
    if (!isRecording) {
      handleMicToggle(true);
    }
  });

  // ── Render ──
  return (
    <div className="flex flex-col h-screen bg-mesh" id="app-root">
      {/* Startup Overlay for Autoplay Policy */}
      {!greetingPlayed && (
        <div 
          onClick={playGreeting}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm cursor-pointer transition-opacity"
        >
          <div className="bg-white/10 border border-white/20 p-8 rounded-3xl text-center shadow-2xl pulse-ring">
            <span className="text-5xl mb-4 block">👋</span>
            <h2 className="text-2xl font-bold text-white mb-2">Welcome to Chulbul AI</h2>
            <p className="text-white/70">Click anywhere to start the assistant.</p>
          </div>
        </div>
      )}

      <Header language={language} onLanguageChange={setLanguage} />

      {/* Main content area */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        
        {/* 3D Orb panel - Made larger and more prominent */}
        <section className="h-[40vh] lg:h-full lg:w-[50%] flex-shrink-0 relative flex items-center justify-center bg-gradient-to-r from-transparent to-black/20">
          <VoiceOrb3D
            frequencyData={frequencyData}
            isActive={isRecording || isLoading}
          />

          {/* Status badge overlaid on the orb */}
          <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-10">
            <span
              className={`
                inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold tracking-wide shadow-lg
                backdrop-blur-xl border
                ${isRecording
                  ? 'bg-red-500/20 border-red-500/50 text-red-300'
                  : isLoading
                    ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                    : 'bg-chulbul-accent/20 border-chulbul-accent/50 text-chulbul-accent-light'
                }
              `}
            >
              <span className={`w-2 h-2 rounded-full ${
                isRecording ? 'bg-red-400 pulse-ring' :
                isLoading ? 'bg-amber-400 animate-pulse' : 'bg-chulbul-success'
              }`} />
              {isRecording ? 'Listening (Say "Chulbul" to wake)…' : isLoading ? 'Thinking…' : 'Ready'}
            </span>
          </div>
        </section>

        {/* Chat panel */}
        <section className="flex-1 flex flex-col min-h-0 border-l border-white/5 bg-black/40 backdrop-blur-3xl z-10 shadow-2xl">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-8 space-y-4 scrollbar-thin" id="chat-messages">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center gap-4 opacity-60">
                <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-chulbul-accent/30 to-purple-500/20 flex items-center justify-center border border-white/10">
                  <span className="text-3xl drop-shadow-md">✨</span>
                </div>
                <p className="text-base text-chulbul-text-muted max-w-[280px]">
                  {language === 'en'
                    ? 'Hey! I\'m Chulbul. Say "Hey Chulbul" to wake me up, or tap the mic.'
                    : 'Namaste! Main Chulbul hoon. "Hey Chulbul" bolo ya mic dabao.'}
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                text={msg.text}
                toolUsed={msg.toolUsed}
              />
            ))}

            {/* Tool Execution Status */}
            {toolStatus && (
              <div className="flex justify-start mb-3">
                <div className="px-4 py-2 rounded-2xl bg-white/5 border border-white/10 text-xs text-white/60 animate-pulse flex items-center gap-2">
                  <svg className="w-4 h-4 text-amber-400/80 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {toolStatus}
                </div>
              </div>
            )}

            {/* Typing indicator */}
            {isLoading && !toolStatus && (
              <div className="flex justify-start mb-3">
                <div className="glass-card px-5 py-4 rounded-2xl rounded-bl-md border border-white/5">
                  <span className="typing-dot bg-chulbul-accent" />
                  <span className="typing-dot bg-chulbul-accent" />
                  <span className="typing-dot bg-chulbul-accent" />
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Input bar */}
          <div className="p-4 border-t border-white/10 bg-black/20">
            <ChatInput
              onSend={handleSend}
              onMicToggle={handleMicToggle}
              isRecording={isRecording}
              disabled={isLoading}
            />
          </div>
        </section>
      </main>
    </div>
  );
}
