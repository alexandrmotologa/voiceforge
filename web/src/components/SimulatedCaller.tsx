import React, { useState } from 'react';
import { Play, Sparkles, Send } from 'lucide-react';

interface SimulatedCallerProps {
  isConnected: boolean;
  onInjectPrompt: (prompt: string) => void;
  onTriggerBargeIn: () => void;
}

export const SimulatedCaller: React.FC<SimulatedCallerProps> = ({
  isConnected,
  onInjectPrompt,
  onTriggerBargeIn
}) => {
  const [customPrompt, setCustomPrompt] = useState('');

  const presets = [
    { label: 'Check Weather', prompt: 'What is the current weather in London?' },
    { label: 'System Health', prompt: 'Check VoiceForge system status and CPU load.' },
    { label: 'Perform Math', prompt: 'Calculate forty-two times eighteen.' },
    { label: 'Explain WebRTC', prompt: 'Explain the benefits of WebRTC Opus audio.' }
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customPrompt.trim()) return;
    onInjectPrompt(customPrompt.trim());
    setCustomPrompt('');
  };

  return (
    <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-5 space-y-4 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <h4 className="font-semibold text-slate-200">Simulated Caller & Prompt Injector</h4>
        </div>
        <span className="text-[11px] text-slate-500">Hands-Free Pipeline Testing</span>
      </div>

      {/* Preset prompt buttons */}
      <div className="flex flex-wrap gap-2">
        {presets.map((p, idx) => (
          <button
            key={idx}
            disabled={!isConnected}
            onClick={() => onInjectPrompt(p.prompt)}
            className="px-3 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 font-medium text-xs flex items-center space-x-1.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Play className="w-3 h-3 text-cyan-400" />
            <span>{p.label}</span>
          </button>
        ))}

        <button
          disabled={!isConnected}
          onClick={onTriggerBargeIn}
          className="px-3 py-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 border border-rose-800/80 text-rose-300 font-semibold text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Test Barge-In Cutoff
        </button>
      </div>

      {/* Custom input form */}
      <form onSubmit={handleSubmit} className="flex items-center space-x-2">
        <input
          type="text"
          value={customPrompt}
          onChange={(e) => setCustomPrompt(e.target.value)}
          placeholder={isConnected ? "Type custom spoken phrase to inject into pipeline..." : "Connect first to inject simulated speech"}
          disabled={!isConnected}
          className="flex-1 p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!isConnected || !customPrompt.trim()}
          className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white font-medium disabled:opacity-40 transition-all shadow-md"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
