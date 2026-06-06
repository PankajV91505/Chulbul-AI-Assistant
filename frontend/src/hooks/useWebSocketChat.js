import { useEffect, useRef, useState, useCallback } from 'react';

export function useWebSocketChat({ language, onTranscript, onChunk, onToolStatus, onDone, onError }) {
    const ws = useRef(null);
    const [isConnected, setIsConnected] = useState(false);

    // Use refs for callbacks to avoid re-creating WebSocket on every render if dependencies change
    const callbacks = useRef({ onTranscript, onChunk, onToolStatus, onDone, onError });
    
    useEffect(() => {
        callbacks.current = { onTranscript, onChunk, onToolStatus, onDone, onError };
    }, [onTranscript, onChunk, onToolStatus, onDone, onError]);

    useEffect(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Connect to FastAPI backend
        const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
        ws.current = new WebSocket(`${protocol}//${host}/ws/chat`);
        
        ws.current.onopen = () => setIsConnected(true);
        ws.current.onclose = () => setIsConnected(false);
        ws.current.onerror = (e) => {
            console.error("WebSocket error", e);
            if(callbacks.current.onError) callbacks.current.onError("WebSocket connection error.");
        };
        
        ws.current.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                switch (data.type) {
                    case 'transcript':
                        if (callbacks.current.onTranscript) callbacks.current.onTranscript(data.text);
                        break;
                    case 'tool_status':
                        if (callbacks.current.onToolStatus) callbacks.current.onToolStatus(data.tool);
                        break;
                    case 'chunk':
                        if (callbacks.current.onChunk) callbacks.current.onChunk(data.text);
                        break;
                    case 'done':
                        if (callbacks.current.onDone) callbacks.current.onDone();
                        break;
                    case 'error':
                        if (callbacks.current.onError) callbacks.current.onError(data.message);
                        break;
                    default:
                        break;
                }
            } catch (err) {
                console.error("Failed to parse WS message", err);
            }
        };

        return () => {
            if (ws.current) ws.current.close();
        };
    }, []);

    const sendAudioChunk = useCallback((blob) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(blob);
        }
    }, []);

    const startInteraction = useCallback(() => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: "start", language }));
        }
    }, [language]);

    const stopInteraction = useCallback(() => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: "stop" }));
        }
    }, []);

    const sendText = useCallback((text) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: "text_input", text, language }));
        }
    }, [language]);

    return { isConnected, sendAudioChunk, startInteraction, stopInteraction, sendText };
}
