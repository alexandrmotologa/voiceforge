import React from 'react';
import { Mic, Settings, Activity, Zap, ShieldCheck } from 'lucide-react';
import { ConnectionState, TurnMetrics } from '../types';

interface HeaderProps {
  connectionState: ConnectionState;
  latestMetrics: TurnMetrics | null;
  onOpenSettings: () => void;
  isLocalMode: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  connectionState,
  latestMetrics,
  onOpenSettings,
  isLocalMode
}) => {
  return (
    <header className="h-16 border-b border-slate-800 bg-[#090d16]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <Mic className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-lg tracking-tight text-white">VoiceForge</span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-medium">
              WebRTC Opus
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium">Real-Time Voice Server & Barge-In Gateway</p>
        </div>
      </div>

      <div className="flex items-center space-x-3 font-mono text-xs">
        {/* Mode pill */}
        <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">
          {isLocalMode ? (
            <>
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-semibold">Local Offline (Cost $0)</span>
            </>
          ) : (
            <>
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-cyan-400 font-semibold">Cloud Speed (&lt;450ms)</span>
            </>
          )}
        </div>

        {/* Turnaround latency metric */}
        {latestMetrics && (
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800">
            <Activity className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
            <span className="text-slate-400">Turnaround:</span>
            <span className={`font-bold ${
              latestMetrics.total_turnaround_ms < 450
                ? 'text-emerald-400'
                : latestMetrics.total_turnaround_ms < 750
                ? 'text-amber-400'
                : 'text-rose-400'
            }`}>
              {latestMetrics.total_turnaround_ms}ms
            </span>
          </div>
        )}

        {/* Connection status pill */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">
          <span className="relative flex h-2 w-2">
            {connectionState === 'connected' && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            )}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${
              connectionState === 'connected'
                ? 'bg-emerald-500'
                : connectionState === 'connecting'
                ? 'bg-amber-500'
                : 'bg-slate-600'
            }`} />
          </span>
          <span className="text-slate-300 capitalize">{connectionState}</span>
        </div>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/80 text-slate-300 transition-colors"
          title="Engine & Voice Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
