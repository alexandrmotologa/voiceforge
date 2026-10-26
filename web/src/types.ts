export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export type SessionState = 'idle' | 'user_speaking' | 'ai_thinking' | 'ai_speaking' | 'interrupted';

export interface TurnMetrics {
  type: 'metrics';
  turn_id: string;
  stt_latency_ms: number;
  llm_ttft_ms: number;
  sentence_split_ms: number;
  tts_first_chunk_ms: number;
  total_turnaround_ms: number;
}

export interface BargeInEvent {
  type: 'barge_in';
  timestamp: number;
  latency_ms: number;
  speech_prob: number;
}

export interface TranscriptMessage {
  id: string;
  speaker: 'user' | 'assistant';
  text: string;
  timestamp: number;
  isInterrupted?: boolean;
  interruptLatencyMs?: number;
}

export interface ToolCallEvent {
  type: 'tool_call';
  status: 'executing' | 'completed';
  tool_name: string;
  arguments?: Record<string, any>;
  filler_spoken?: string;
  result?: Record<string, any>;
  duration_ms?: number;
}

export interface NetworkStats {
  rtt_ms: number;
  jitter_ms: number;
  packet_loss_percent: number;
  bitrate_kbps: number;
  quality: 'excellent' | 'good' | 'fair' | 'poor';
}

export interface SessionConfig {
  stt_provider: 'deepgram' | 'whisper_local' | 'fallback';
  llm_provider: 'anthropic' | 'openai' | 'ollama' | 'fallback';
  tts_provider: 'cartesia' | 'elevenlabs' | 'native';
  vad_threshold: number;
  voice_id: string;
  speech_rate: number;
  persona_preset?: string;
  system_prompt?: string;
}
