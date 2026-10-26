import React from 'react';
import { Timer } from 'lucide-react';
import { TurnMetrics } from '../types';

interface LatencyWaterfallProps {
  metrics: TurnMetrics | null;
  history: TurnMetrics[];
}

export const LatencyWaterfall: React.FC<LatencyWaterfallProps> = ({ metrics, history }) => {
  if (!metrics) {
    return (
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 flex flex-col items-center justify-center text-center space-y-2 text-slate-500 font-mono text-xs min-h-[220px]">
        <Timer className="w-8 h-8 text-slate-600 mb-2" />
        <p className="font-semibold text-slate-400">Waiting for first conversational turn</p>
        <p className="max-w-xs text-slate-500">
          Speak into your microphone. VoiceForge will measure and render the exact turnaround waterfall breakdown here.
        </p>
      </div>
    );
  }

  const stages = [
    { name: 'STT Transcription', latency: metrics.stt_latency_ms, color: 'bg-cyan-500' },
    { name: 'LLM First Token (TTFT)', latency: metrics.llm_ttft_ms, color: 'bg-indigo-500' },
    { name: 'Sentence Splitter', latency: metrics.sentence_split_ms, color: 'bg-purple-500' },
    { name: 'TTS Audio Chunk', latency: metrics.tts_first_chunk_ms, color: 'bg-emerald-500' }
  ];

  const total = Math.max(1, metrics.total_turnaround_ms);

  return (
    <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Timer className="w-4 h-4 text-cyan-400" />
          <h3 className="font-semibold text-sm text-slate-200">Turnaround Latency Waterfall</h3>
        </div>
        <div className="flex items-center space-x-2 font-mono text-xs">
          <span className="text-slate-400">Total Turnaround:</span>
          <span className={`px-2 py-0.5 rounded font-bold ${
            metrics.total_turnaround_ms < 450
              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
              : metrics.total_turnaround_ms < 750
              ? 'bg-amber-950 text-amber-400 border border-amber-800'
              : 'bg-rose-950 text-rose-400 border border-rose-800'
          }`}>
            {metrics.total_turnaround_ms} ms
          </span>
        </div>
      </div>

      {/* Stage Breakdown Progress Bar */}
      <div className="space-y-3 font-mono text-xs">
        {/* Cumulative bar */}
        <div className="h-3 w-full rounded-full bg-slate-800 overflow-hidden flex">
          {stages.map((st, i) => {
            const pct = (st.latency / total) * 100;
            return (
              <div
                key={i}
                style={{ width: `${pct}%` }}
                className={`h-full ${st.color} transition-all duration-500`}
                title={`${st.name}: ${st.latency}ms`}
              />
            );
          })}
        </div>

        {/* Detailed Stages Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          {stages.map((st, idx) => (
            <div key={idx} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="flex items-center space-x-1.5 text-[11px] text-slate-400">
                <span className={`w-2 h-2 rounded-full ${st.color}`} />
                <span className="truncate">{st.name}</span>
              </div>
              <div className="text-base font-bold text-slate-100">
                {st.latency} <span className="text-[11px] font-normal text-slate-500">ms</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Turn history count */}
      {history.length > 1 && (
        <div className="text-right text-[11px] font-mono text-slate-500">
          Showing turn #{history.length} (Average turnaround: {
            Math.round(history.reduce((acc, h) => acc + h.total_turnaround_ms, 0) / history.length)
          }ms)
        </div>
      )}
    </div>
  );
};
