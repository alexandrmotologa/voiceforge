import { useState, useRef, useEffect, useCallback } from 'react';
import {
  ConnectionState,
  SessionState,
  TurnMetrics,
  BargeInEvent,
  TranscriptMessage,
  ToolCallEvent,
  SessionConfig,
  NetworkStats
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
  const [networkStats, setNetworkStats] = useState<NetworkStats | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const statsIntervalRef = useRef<any>(null);

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

        // Fast pause/restart local playback
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

  // Expose test injector for visual testing
  useEffect(() => {
    (window as any).__voiceforge_inject = (payload: any) => {
      handleDataChannelMessage({ data: JSON.stringify(payload) } as any);
    };
  }, [handleDataChannelMessage]);

  // Monitor WebRTC network metrics (RTT, Jitter, Packet loss)
  const pollNetworkStats = useCallback(async () => {
    const pc = pcRef.current;
    if (!pc || pc.connectionState !== 'connected') return;

    try {
      const stats = await pc.getStats();
      let rtt = 18;
      let jitter = 2;
      let packetsLost = 0;
      let packetsReceived = 1;
      let bitrate = 64;

      stats.forEach((report) => {
        if (report.type === 'candidate-pair' && report.state === 'succeeded') {
          if (report.currentRoundTripTime !== undefined) {
            rtt = Math.round(report.currentRoundTripTime * 1000);
          }
        }
        if (report.type === 'inbound-rtp' && report.kind === 'audio') {
          if (report.jitter !== undefined) jitter = Math.round(report.jitter * 1000);
          if (report.packetsLost !== undefined) packetsLost = report.packetsLost;
          if (report.packetsReceived !== undefined) packetsReceived = report.packetsReceived;
        }
      });

      const lossPct = packetsReceived > 0 ? (packetsLost / (packetsLost + packetsReceived)) * 100 : 0;
      let quality: 'excellent' | 'good' | 'fair' | 'poor' = 'excellent';
      if (rtt > 220 || lossPct > 3) quality = 'poor';
      else if (rtt > 120 || lossPct > 1) quality = 'fair';
      else if (rtt > 60) quality = 'good';

      setNetworkStats({
        rtt_ms: rtt,
        jitter_ms: jitter,
        packet_loss_percent: Math.round(lossPct * 10) / 10,
        bitrate_kbps: bitrate,
        quality
      });
    } catch (e) {
      console.debug('Failed to query WebRTC stats:', e);
    }
  }, []);

  const connect = useCallback(async (config: SessionConfig, audioInputDeviceId?: string) => {
    try {
      setConnectionState('connecting');
      setErrorMsg(null);

      // 1. Capture microphone audio stream
      const constraints: MediaStreamConstraints = {
        audio: {
          deviceId: audioInputDeviceId ? { exact: audioInputDeviceId } : undefined,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000
        }
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
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
          // Start network stats polling
          if (statsIntervalRef.current) clearInterval(statsIntervalRef.current);
          statsIntervalRef.current = setInterval(pollNetworkStats, 2000);
        } else if (pc.connectionState === 'failed' || pc.connectionState === 'closed') {
          setConnectionState('disconnected');
          if (statsIntervalRef.current) clearInterval(statsIntervalRef.current);
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
  }, [handleDataChannelMessage, pollNetworkStats]);

  const disconnect = useCallback(() => {
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current);
      statsIntervalRef.current = null;
    }
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
    setNetworkStats(null);
  }, []);

  const manualInterrupt = useCallback(() => {
    if (dcRef.current && dcRef.current.readyState === 'open') {
      dcRef.current.send(JSON.stringify({ type: 'interrupt' }));
    } else if (sessionId) {
      fetch(`/session/${sessionId}/interrupt`, { method: 'POST' }).catch(console.error);
    }
  }, [sessionId]);

  const injectPrompt = useCallback(async (promptText: string) => {
    if (!sessionId) return;
    try {
      await fetch(`/session/${sessionId}/inject-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText })
      });
    } catch (e) {
      console.error('Failed to inject simulated prompt:', e);
    }
  }, [sessionId]);

  const downloadRecording = useCallback(() => {
    if (!sessionId) return;
    window.open(`/session/${sessionId}/recording`, '_blank');
  }, [sessionId]);

  const exportReport = useCallback(async (format: 'json' | 'markdown') => {
    if (!sessionId) return;
    try {
      const res = await fetch(`/session/${sessionId}/report?format=${format}`);
      const text = await res.text();
      const blob = new Blob([text], {
        type: format === 'markdown' ? 'text/markdown' : 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `voiceforge_report_${sessionId}.${format === 'markdown' ? 'md' : 'json'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export report error:', e);
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
    networkStats,
    errorMsg,
    localStream: localStreamRef.current,
    connect,
    disconnect,
    manualInterrupt,
    injectPrompt,
    downloadRecording,
    exportReport
  };
}
