/**
 * App.jsx — Root component for Chulbul AI frontend.
 *
 * Layout: Header | 3D Orb (left) + Chat Panel (right) | Input Bar
 * On mobile the 3D orb sits above the chat panel.
 */

import { useState, useRef, useEffect, useCallback } from 'react';

import Header from './components/Header';
import VoiceOrb3D from './components/VoiceOrb3D';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';

import { useVoiceRecorder } from './hooks/useVoiceRecorder';
import { useAudioAnalyser } from './hooks/useAudioAnalyser';
import { sendMessage, sendVoice, getAudioUrl } from './api';

export default function App() {
  // ── State ──
  const [messages, setMessages] = useState([]);
  const [language, setLanguage] = useState('en');
  const [sessionId, setSessionId] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // ── Hooks ──
  const { isRecording, startRecording, stopRecording } = useVoiceRecorder();
  const { frequencyData, connect, disconnect } = useAudioAnalyser();

  // ── Refs ──
  const chatEndRef = useRef(null);
  const audioRef = useRef(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // ── Helpers ──
  const addMessage = useCallback((role, text, toolUsed = 'direct_response') => {
    setMessages((prev) => [...prev, { id: Date.now(), role, text, toolUsed }]);
  }, []);

  const playAudio = useCallback((audioUrl) => {
    if (!audioUrl) return;
    const fullUrl = getAudioUrl(audioUrl);
    if (!fullUrl) return;

    const audio = new Audio(fullUrl);
    audioRef.current = audio;

    audio.addEventListener('canplaythrough', () => {
      audio.play().catch(() => {});
      // Feed audio to the analyser for 3D visualisation
      try {
        connect(audio);
      } catch {
        // Already connected or cross-origin — ignore
      }
    });

    audio.addEventListener('ended', () => {
      disconnect();
    });
  }, [connect, disconnect]);

  // ── Handlers ──
  const handleSend = useCallback(async (text) => {
    addMessage('user', text);
    setIsLoading(true);

    try {
      const res = await sendMessage(text, language, sessionId);
      if (res.session_id) setSessionId(res.session_id);
      addMessage('assistant', res.text, res.tool_used);
      playAudio(res.audio_url);
    } catch (err) {
      addMessage('assistant', `Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [language, sessionId, addMessage, playAudio]);

  const handleMicToggle = useCallback(async () => {
    if (isRecording) {
      const blob = await stopRecording();
      if (!blob) return;

      addMessage('user', '🎤 [Voice message]');
      setIsLoading(true);

      try {
        const res = await sendVoice(blob, language, sessionId);
        if (res.session_id) setSessionId(res.session_id);
        addMessage('assistant', res.text, res.tool_used);
        playAudio(res.audio_url);
      } catch (err) {
        addMessage('assistant', `Error: ${err.message}`);
      } finally {
        setIsLoading(false);
      }
    } else {
      await startRecording();
    }
  }, [isRecording, startRecording, stopRecording, language, sessionId, addMessage, playAudio]);

  // ── Render ──
  return (
    <div className="flex flex-col h-screen bg-mesh" id="app-root">
      <Header language={language} onLanguageChange={setLanguage} />

      {/* Main content area */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* 3D Orb panel */}
        <section className="h-[35vh] lg:h-full lg:w-[45%] flex-shrink-0 relative">
          <VoiceOrb3D
            frequencyData={frequencyData}
            isActive={isRecording || isLoading}
          />

          {/* Status badge overlaid on the orb */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
            <span
              className={`
                inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium
                backdrop-blur-md border
                ${isRecording
                  ? 'bg-red-500/10 border-red-500/30 text-red-400'
                  : isLoading
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                    : 'bg-chulbul-accent/10 border-chulbul-accent/30 text-chulbul-accent-light'
                }
              `}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${
                isRecording ? 'bg-red-400 pulse-ring' :
                isLoading ? 'bg-amber-400 animate-pulse' : 'bg-chulbul-success'
              }`} />
              {isRecording ? 'Listening…' : isLoading ? 'Thinking…' : 'Ready'}
            </span>
          </div>
        </section>

        {/* Chat panel */}
        <section className="flex-1 flex flex-col min-h-0 border-l border-chulbul-border/30">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1" id="chat-messages">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center gap-3 opacity-60">
                <div className="w-14 h-14 rounded-2xl bg-chulbul-accent/10 flex items-center justify-center">
                  <span className="text-2xl">✨</span>
                </div>
                <p className="text-sm text-chulbul-text-muted max-w-[260px]">
                  {language === 'en'
                    ? 'Hey! I\'m Chulbul. Ask me anything or tap the mic to talk.'
                    : 'Namaste! Main Chulbul hoon. Kuch bhi pucho ya mic dabao.'}
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

            {/* Typing indicator */}
            {isLoading && (
              <div className="flex justify-start mb-3">
                <div className="glass-card px-4 py-3 rounded-2xl rounded-bl-md">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Input bar */}
          <div className="p-3 border-t border-chulbul-border/30">
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
