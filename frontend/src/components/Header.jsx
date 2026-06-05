/**
 * Header — top navigation bar with branding and language toggle.
 */

import { useState } from 'react';

export default function Header({ language, onLanguageChange }) {
  return (
    <header className="flex items-center justify-between px-5 py-3 border-b border-chulbul-border/50">
      {/* Logo / Brand */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-chulbul-accent to-purple-400
                        flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-chulbul-glow">
          C
        </div>
        <div>
          <h1 className="text-base font-semibold gradient-text leading-tight">Chulbul AI</h1>
          <p className="text-[10px] text-chulbul-text-muted tracking-wide">Smart Assistant</p>
        </div>
      </div>

      {/* Language toggle */}
      <div className="flex items-center gap-1 bg-chulbul-surface rounded-lg p-0.5">
        <button
          onClick={() => onLanguageChange('en')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200
            ${language === 'en'
              ? 'bg-chulbul-accent text-white shadow-md shadow-chulbul-glow'
              : 'text-chulbul-text-muted hover:text-chulbul-text'
            }`}
          id="lang-en-btn"
        >
          EN
        </button>
        <button
          onClick={() => onLanguageChange('hi')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200
            ${language === 'hi'
              ? 'bg-chulbul-accent text-white shadow-md shadow-chulbul-glow'
              : 'text-chulbul-text-muted hover:text-chulbul-text'
            }`}
          id="lang-hi-btn"
        >
          हिं
        </button>
      </div>
    </header>
  );
}
