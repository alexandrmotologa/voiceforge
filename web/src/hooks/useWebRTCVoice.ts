import { useState, useRef, useEffect, useCallback } from 'react';
import {
  ConnectionState,
  SessionState,
  TurnMetrics,
  BargeInEvent,
  TranscriptMessage,
  ToolCallEvent,
  SessionConfig
} from '../types';

export function useWebRTCVoice() {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [sessionState, setSessionState] = useState<SessionState>('idle');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([]);
  const [metrics, setMetrics] = useState<TurnMetrics | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<TurnMetrics[]>([]);
  const [latestBargeIn, setLatestBargeIn] = useState<BargeInEvent | null>(null);
  const [toolCalls, setToolCalls] = useState<ToolCallEvent[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);

  // Initialize invisible audio element for playback
  useEffect(() => {
    const audio = new Audio();
    audio.autoplay = true;
    audioElementRef.current = audio;

    return () => {
      audio.srcObject = null;
    };
  }, []);

  const handleDataChannelMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'state') {
        setSessionState(data.state as SessionState);
      } else if (data.type === 'transcript') {
        setTranscripts((prev) => {
          const newMessage: TranscriptMessage = {
            id: `msg_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
            speaker: data.speaker,
            text: data.text,
            timestamp: data.timestamp || Date.now()
          };
          return [...prev, newMessage];
        });
      } else if (data.type === 'barge_in') {
        const bargeInEv: BargeInEvent = data;
        setLatestBargeIn(bargeInEv);
        setSessionState('interrupted');

        // Mark the last assistant message as interrupted
        setTranscripts((prev) => {
          if (prev.length === 0) return prev;
          const copy = [...prev];
          for (let i = copy.length - 1; i >= 0; i--) {
            if (copy[i].speaker === 'assistant') {
              copy[i] = {
                ...copy[i],
                isInterrupted: true,
                interruptLatencyMs: bargeInEv.latency_ms
              };
              break;
            }
          }
          return copy;
        });

        // Fast fade-out/pause local playback immediately
        if (audioElementRef.current) {
          audioElementRef.current.pause();
          setTimeout(() => {
            if (audioElementRef.current) audioElementRef.current.play().catch(() => {});
          }, 50);
        }
      } else if (data.type === 'metrics') {
        setMetrics(data as TurnMetrics);
        setMetricsHistory((prev) => [...prev, data as TurnMetrics]);
      } else if (data.type === 'tool_call') {
        setToolCalls((prev) => [...prev, data as ToolCallEvent]);
      }
    } catch (err) {
      console.error('Failed to parse data channel message:', err);
    }
  }, []);

  // Expose test injector for studio testing & visual verification
  useEffect(() => {
    (window as any).__voiceforge_inject = (payload: any) => {
      handleDataChannelMessage({ data: JSON.stringify(payload) } as any);
    };
  }, [handleDataChannelMessage]);

  const connect = useCallback(async (config: SessionConfig) => {
    try {
      setConnectionState('connecting');
      setErrorMsg(null);

      // 1. Capture microphone audio stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000
        }
      });
      localStreamRef.current = stream;

      // 2. Instantiate RTCPeerConnection
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      });
      pcRef.current = pc;

      // Add local audio tracks to peer connection
      stream.getTracks().forEach((track) => pc.addTrack(track, stream));

      // 3. Listen for remote audio track from server
      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          if (audioElementRef.current) {
            audioElementRef.current.srcObject = event.streams[0];
          }
        }
      };

      // 4. Create WebRTC Data Channel
      const dc = pc.createDataChannel('voiceforge-events');
      dcRef.current = dc;
      dc.onopen = () => console.log('WebRTC Data Channel opened');
      dc.onmessage = handleDataChannelMessage;

      pc.ondatachannel = (ev) => {
        ev.channel.onmessage = handleDataChannelMessage;
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'connected') {
          setConnectionState('connected');
        } else if (pc.connectionState === 'failed' || pc.connectionState === 'closed') {
          setConnectionState('disconnected');
        }
      };

      // 5. Create SDP Offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // 6. Send Offer to VoiceForge server
      const response = await fetch('/session/offer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: offer.sdp,
          type: offer.type,
          config: config
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const answerData = await response.json();
      setSessionId(answerData.session_id);

      // 7. Set Remote SDP Answer
      await pc.setRemoteDescription(new RTCSessionDescription({
        type: answerData.type,
        sdp: answerData.sdp
      }));

      // Listen for local ICE candidates and send to server
      pc.onicecandidate = (event) => {
        if (event.candidate && answerData.session_id) {
          fetch('/session/ice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: answerData.session_id,
              candidate: event.candidate.candidate,
              sdpMid: event.candidate.sdpMid,
              sdpMLineIndex: event.candidate.sdpMLineIndex
            })
          }).catch(console.error);
        }
      };

    } catch (err: any) {
      console.error('Connection failed:', err);
      setErrorMsg(err.message || 'Failed to establish WebRTC connection');
      setConnectionState('error');
      disconnect();
    }
  }, [handleDataChannelMessage]);

  const disconnect = useCallback(() => {
    if (dcRef.current) {
      dcRef.current.close();
      dcRef.current = null;
    }
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((t) => t.stop());
      localStreamRef.current = null;
    }
    if (audioElementRef.current) {
      audioElementRef.current.srcObject = null;
    }
    setConnectionState('disconnected');
    setSessionState('idle');
  }, []);

  const manualInterrupt = useCallback(() => {
    if (dcRef.current && dcRef.current.readyState === 'open') {
      dcRef.current.send(JSON.stringify({ type: 'interrupt' }));
    } else if (sessionId) {
      fetch(`/session/${sessionId}/interrupt`, { method: 'POST' }).catch(console.error);
    }
  }, [sessionId]);

  return {
    connectionState,
    sessionState,
    sessionId,
    transcripts,
    metrics,
    metricsHistory,
    latestBargeIn,
    toolCalls,
    errorMsg,
    localStream: localStreamRef.current,
    connect,
    disconnect,
    manualInterrupt
  };
}
