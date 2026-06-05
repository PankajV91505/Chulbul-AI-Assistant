/**
 * ChatInput — text input bar with send button and mic toggle.
 */

import { useState, useRef, useEffect } from 'react';

export default function ChatInput({ onSend, onMicToggle, isRecording, disabled }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);

  // Auto-focus on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 p-3 glass-card"
      id="chat-input-form"
    >
      {/* Mic button */}
      <button
        type="button"
        onClick={onMicToggle}
        disabled={disabled}
        className={`
          relative flex items-center justify-center w-10 h-10 rounded-full
          transition-all duration-300
          ${isRecording
            ? 'bg-red-500/20 text-red-400'
            : 'bg-chulbul-surface-hover text-chulbul-text-muted hover:text-chulbul-accent-light'
          }
        `}
        aria-label={isRecording ? 'Stop recording' : 'Start recording'}
      >
        {isRecording && (
          <span className="absolute inset-0 rounded-full bg-red-500/30 pulse-ring" />
        )}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="w-5 h-5 relative z-10"
        >
          {isRecording ? (
            <rect x="6" y="6" width="12" height="12" rx="2" />
          ) : (
            <path d="M12 1a4 4 0 0 1 4 4v6a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4Zm-1 17.93A7.01 7.01 0 0 1 5 12h2a5 5 0 0 0 10 0h2a7.01 7.01 0 0 1-6 6.93V21h3v2H8v-2h3v-2.07Z" />
          )}
        </svg>
      </button>

      {/* Text input */}
      <input
        ref={inputRef}
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        placeholder={isRecording ? 'Listening…' : 'Type a message…'}
        className="flex-1 bg-transparent border-none outline-none text-sm text-chulbul-text
                   placeholder:text-chulbul-text-muted"
        id="chat-text-input"
      />

      {/* Send button */}
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="flex items-center justify-center w-10 h-10 rounded-full
                   btn-glow disabled:opacity-30 disabled:cursor-not-allowed
                   disabled:shadow-none disabled:transform-none"
        aria-label="Send message"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="w-4 h-4"
        >
          <path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" />
        </svg>
      </button>
    </form>
  );
}
