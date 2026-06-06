/**
 * Custom hook for microphone recording via MediaRecorder API.
 * Returns an audio Blob when recording is stopped.
 */

import { useState, useRef, useCallback } from 'react';

export function useVoiceRecorder(onChunk) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);
  const [stream, setStream] = useState(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setStream(mediaStream);
      const recorder = new MediaRecorder(mediaStream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      });

      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
          if (onChunk) onChunk(e.data);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start(100); // collect chunks every 100ms
      setIsRecording(true);
    } catch (err) {
      setError('Microphone access denied or unavailable.');
      console.error('Mic error:', err);
    }
  }, []);

  const stopRecording = useCallback(() => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === 'inactive') {
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        // Stop all tracks to release the mic
        recorder.stream.getTracks().forEach((t) => t.stop());
        setIsRecording(false);
        setStream(null);
        resolve(blob);
      };

      recorder.stop();
    });
  }, []);

  return { isRecording, startRecording, stopRecording, error, stream };
}
