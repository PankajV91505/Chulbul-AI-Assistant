/**
 * Hook for Wake Word Detection ("Hey Chulbul" / "Chulbul")
 * Uses the Web Speech API (SpeechRecognition).
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export function useWakeWord(onWakeWordDetected) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);
  const recognitionRef = useRef(null);

  const startListening = useCallback(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setError('Speech recognition not supported in this browser. Use Chrome/Edge.');
      return;
    }

    try {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US'; // Listen in English for "Hey Chulbul"
      
      recognition.onstart = () => {
        console.log('🎤 Wake Word listener started. Waiting for "Chulbul"...');
        setIsListening(true);
      };
      
      recognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript.toLowerCase().trim();
          
          // Log what the browser is actually hearing
          if (transcript) {
             console.log(`👂 Browser heard: "${transcript}"`);
          }

          // Broad match for Indian accents / varied pronunciations
          const isWakeWord = /chulbul|chul bul|chilbul|shulbul|chulbuli|hey chulbul/i.test(transcript);
          
          if (isWakeWord) {
            console.log('🚀 WAKE WORD DETECTED! Activating Mic...');
            // Stop recognition immediately to free up mic for actual recording
            recognition.stop();
            onWakeWordDetected();
            return;
          }
        }
      };

      recognition.onerror = (e) => {
        if (e.error === 'not-allowed') {
          setError('Microphone access denied.');
        }
      };

      recognition.onend = () => {
        // Automatically restart listening if it stopped and we want it to keep listening
        // Only restart if we still want to be listening (e.g. state is still true)
        if (isListening) {
          try { recognition.start(); } catch {}
        } else {
          setIsListening(false);
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('Wake word start error:', err);
    }
  }, [onWakeWordDetected, isListening]);

  const stopListening = useCallback(() => {
    setIsListening(false);
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  }, []);

  useEffect(() => {
    // Auto-start listening on mount
    startListening();
    return () => stopListening();
  }, [startListening, stopListening]);

  return { isListening, stopListening, startListening, error };
}
