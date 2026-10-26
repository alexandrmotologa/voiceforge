import React, { useState } from 'react';
import { Header } from './components/Header';
import { Visualizer } from './components/Visualizer';
import { LatencyWaterfall } from './components/LatencyWaterfall';
import { TranscriptView } from './components/TranscriptView';
import { ToolMonitor } from './components/ToolMonitor';
import { SettingsModal } from './components/SettingsModal';
import { useWebRTCVoice } from './hooks/useWebRTCVoice';
import { useAudioVisualizer } from './hooks/useAudioVisualizer';
import { SessionConfig } from './types';

export const App: React.FC = () => {
  const [config, setConfig] = useState<SessionConfig>({
    stt_provider: 'fallback',
    llm_provider: 'fallback',
    tts_provider: 'native',
    vad_threshold: 0.5,
    voice_id: 'en_default'
  });
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const {
    connectionState,
    sessionState,
    transcripts,
    metrics,
    metricsHistory,
    latestBargeIn,
    toolCalls,
    errorMsg,
    localStream,
    connect,
    disconnect,
    manualInterrupt
  } = useWebRTCVoice();

  const { volume } = useAudioVisualizer(localStream, connectionState === 'connected');

  const isLocalMode = config.stt_provider === 'fallback' && config.llm_provider === 'fallback';

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans">
      <Header
        connectionState={connectionState}
        latestMetrics={metrics}
        onOpenSettings={() => setIsSettingsOpen(true)}
        isLocalMode={isLocalMode}
      />

      {errorMsg && (
        <div className="bg-rose-950/80 border-b border-rose-800 text-rose-300 px-6 py-2.5 text-xs font-mono flex items-center justify-between">
          <span>Error: {errorMsg}</span>
          <button onClick={() => window.location.reload()} className="underline hover:text-white">
            Reload
          </button>
        </div>
      )}

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Main Interactive Visualizer */}
        <Visualizer
          connectionState={connectionState}
          sessionState={sessionState}
          audioVolume={volume}
          latestBargeIn={latestBargeIn}
          onConnect={() => connect(config)}
          onDisconnect={disconnect}
          onInterrupt={manualInterrupt}
        />

        {/* Turnaround Latency Waterfall Breakdown */}
        <LatencyWaterfall
          metrics={metrics}
          history={metricsHistory}
        />

        {/* Two-column layout: Dialogue transcript & Tool execution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TranscriptView
            transcripts={transcripts}
            toolCalls={toolCalls}
          />

          <ToolMonitor
            toolCalls={toolCalls}
          />
        </div>
      </main>

      <footer className="border-t border-slate-800/80 py-4 px-6 text-center text-xs font-mono text-slate-500">
        VoiceForge • Self-Hosted WebRTC Voice Gateway • Sub-80ms Barge-In with Silero VAD v5
      </footer>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={config}
        onSaveConfig={(newCfg) => setConfig(newCfg)}
      />
    </div>
  );
};

export default App;
