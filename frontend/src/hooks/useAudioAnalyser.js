/**
 * Custom hook for analysing an audio stream's frequency data via
 * Web Audio API. Provides a Float32Array of frequency amplitudes
 * that can drive 3D visualisation.
 */

import { useRef, useEffect, useCallback, useState } from 'react';

export function useAudioAnalyser(fftSize = 256) {
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);
  const [frequencyData, setFrequencyData] = useState(() => new Float32Array(fftSize / 2));
  const rafRef = useRef(null);

  /** Connect an HTMLAudioElement or MediaStream to the analyser. */
  const connect = useCallback((source) => {
    // Create AudioContext on first use (must happen after user gesture)
    if (!audioCtxRef.current) {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    const ctx = audioCtxRef.current;

    // Create analyser node
    if (!analyserRef.current) {
      const analyser = ctx.createAnalyser();
      analyser.fftSize = fftSize;
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;
    }

    // Disconnect previous source if any
    if (sourceRef.current) {
      try { sourceRef.current.disconnect(); } catch { /* noop */ }
    }

    // Create source node
    let node;
    if (source instanceof MediaStream) {
      node = ctx.createMediaStreamSource(source);
    } else if (source instanceof HTMLAudioElement) {
      node = ctx.createMediaElementSource(source);
      source.crossOrigin = 'anonymous';
    } else {
      return;
    }

    node.connect(analyserRef.current);
    // analyserRef.current.connect(ctx.destination); // Do NOT connect mic to speakers (causes feedback/echo)
    sourceRef.current = node;

    // Start the analysis loop
    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Float32Array(bufferLength);

    const tick = () => {
      analyserRef.current.getFloatFrequencyData(dataArray);
      // Normalise from dB (-100..0) to 0..1
      const normalised = new Float32Array(bufferLength);
      for (let i = 0; i < bufferLength; i++) {
        normalised[i] = Math.max(0, (dataArray[i] + 100) / 100);
      }
      setFrequencyData(normalised);
      rafRef.current = requestAnimationFrame(tick);
    };
    tick();
  }, [fftSize]);

  /** Disconnect and clean up. */
  const disconnect = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (sourceRef.current) {
      try { sourceRef.current.disconnect(); } catch { /* noop */ }
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
      if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
        audioCtxRef.current.close();
      }
    };
  }, [disconnect]);

  return { frequencyData, connect, disconnect };
}
