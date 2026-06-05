/**
 * API client for the Chulbul AI backend.
 * Handles text chat, voice upload, streaming, and audio playback.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '/api';

/**
 * Send a text message and receive the full agent response.
 */
export async function sendMessage(message, language = 'en', sessionId = '') {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      language,
      session_id: sessionId,
    }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Chat request failed');
  }

  return res.json();
}

/**
 * Send an audio blob for transcription + agent processing.
 */
export async function sendVoice(audioBlob, language = 'en', sessionId = '') {
  const form = new FormData();
  form.append('audio', audioBlob, 'recording.webm');
  form.append('language', language);
  form.append('session_id', sessionId);

  const res = await fetch(`${BASE_URL}/voice`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Voice request failed');
  }

  return res.json();
}

/**
 * Send an audio blob for instant transcription.
 */
export async function transcribeAudio(audioBlob, language = 'en') {
  const form = new FormData();
  form.append('audio', audioBlob, 'recording.webm');
  form.append('language', language);

  const res = await fetch(`${BASE_URL}/transcribe`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Transcription failed');
  }

  return res.json();
}

/**
 * Generate TTS audio from text.
 */
export async function generateTTS(text, language = 'en') {
  const res = await fetch(`${BASE_URL}/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  });

  if (!res.ok) {
    throw new Error('TTS generation failed');
  }

  return res.json();
}

/**
 * Stream text from the /chat/stream SSE endpoint.
 * Calls `onChunk` for each text fragment, `onTool` for tool status, and `onDone` when complete.
 */
export async function streamMessage(message, language = 'en', { onChunk, onTool, onDone, onError }) {
  try {
    const res = await fetch(`${BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, language }),
    });

    if (!res.ok) throw new Error('Stream request failed');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            onDone?.();
            return;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'chunk') {
              onChunk?.(parsed.text);
            } else if (parsed.type === 'tool_status') {
              onTool?.(parsed.tool);
            }
          } catch (e) {
            // fallback if not json
            onChunk?.(data);
          }
        }
      }
    }

    onDone?.();
  } catch (err) {
    onError?.(err);
  }
}

/**
 * Get the full URL for an audio file served by the backend.
 */
export function getAudioUrl(path) {
  if (!path) return null;
  // path is like "/audio/chulbul_abc123.mp3"
  return `${BASE_URL}${path}`;
}
