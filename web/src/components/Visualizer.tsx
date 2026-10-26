import React, { useEffect, useRef } from 'react';
import { Mic, MicOff, Hand, ShieldAlert } from 'lucide-react';
import { ConnectionState, SessionState, BargeInEvent } from '../types';

interface VisualizerProps {
  connectionState: ConnectionState;
  sessionState: SessionState;
  audioVolume: number;
  latestBargeIn: BargeInEvent | null;
  onConnect: () => void;
  onDisconnect: () => void;
  onInterrupt: () => void;
}

export const Visualizer: React.FC<VisualizerProps> = ({
  connectionState,
  sessionState,
  audioVolume,
  latestBargeIn,
  onConnect,
  onDisconnect,
  onInterrupt
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      phase += 0.05;

      // Color selection based on conversational state
      let strokeColor = '#334155'; // idle
      let shadowColor = 'transparent';
      let amplitude = 10;

      if (sessionState === 'user_speaking') {
        strokeColor = '#10b981'; // emerald green
        shadowColor = 'rgba(16, 185, 129, 0.4)';
        amplitude = 25 + audioVolume * 90;
      } else if (sessionState === 'ai_speaking') {
        strokeColor = '#a855f7'; // purple
        shadowColor = 'rgba(168, 85, 247, 0.4)';
        amplitude = 35 + Math.sin(phase * 2) * 15;
      } else if (sessionState === 'ai_thinking') {
        strokeColor = '#06b6d4'; // cyan
        shadowColor = 'rgba(6, 182, 212, 0.3)';
        amplitude = 15 + Math.sin(phase * 4) * 8;
      } else if (sessionState === 'interrupted') {
        strokeColor = '#f43f5e'; // rose/red
        shadowColor = 'rgba(244, 63, 94, 0.6)';
        amplitude = 50;
      }

      ctx.save();
      ctx.lineWidth = 3;
      ctx.strokeStyle = strokeColor;
      ctx.shadowColor = shadowColor;
      ctx.shadowBlur = 12;
      ctx.beginPath();

      const numBars = 48;
      const barWidth = width / numBars;

      for (let i = 0; i < numBars; i++) {
        const x = i * barWidth;
        const norm = i / numBars;
        // Window function (hanning) to taper edges
        const windowFactor = Math.sin(norm * Math.PI);
        const wave = Math.sin(norm * 12 + phase) * Math.cos(norm * 6 - phase);
        const barHeight = amplitude * windowFactor * (0.3 + 0.7 * Math.abs(wave));

        ctx.moveTo(x + barWidth / 2, centerY - barHeight);
        ctx.lineTo(x + barWidth / 2, centerY + barHeight);
      }

      ctx.stroke();
      ctx.restore();

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [sessionState, audioVolume]);

  const isConnected = connectionState === 'connected';

  return (
    <div className="relative rounded-2xl bg-slate-900/60 border border-slate-800/80 p-6 backdrop-blur-md overflow-hidden">
      {/* Background ambient glow */}
      <div className={`absolute -top-24 -left-24 w-64 h-64 rounded-full blur-3xl pointer-events-none transition-all duration-700 ${
        sessionState === 'user_speaking'
          ? 'bg-emerald-500/15'
          : sessionState === 'ai_speaking'
          ? 'bg-purple-500/15'
          : sessionState === 'interrupted'
          ? 'bg-rose-500/25'
          : 'bg-cyan-500/10'
      }`} />

      <div className="flex flex-col items-center justify-center space-y-6">
        {/* State description badge */}
        <div className="flex items-center space-x-2 font-mono text-xs">
          <span className="text-slate-400">Current Pipeline State:</span>
          <span className={`px-2.5 py-1 rounded-md font-semibold capitalize border ${
            sessionState === 'user_speaking'
              ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800'
              : sessionState === 'ai_speaking'
              ? 'bg-purple-950/80 text-purple-400 border-purple-800'
              : sessionState === 'ai_thinking'
              ? 'bg-cyan-950/80 text-cyan-400 border-cyan-800 animate-pulse'
              : sessionState === 'interrupted'
              ? 'bg-rose-950/80 text-rose-400 border-rose-800 font-bold'
              : 'bg-slate-800 text-slate-300 border-slate-700'
          }`}>
            {sessionState.replace('_', ' ')}
          </span>
        </div>

        {/* Audio Waveform Canvas */}
        <div className="w-full h-36 flex items-center justify-center relative">
          <canvas
            ref={canvasRef}
            width={700}
            height={140}
            className="w-full h-full max-w-2xl"
          />

          {/* Barge-in alert overlay */}
          {latestBargeIn && (
            <div className="absolute top-2 right-4 flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-rose-950/90 text-rose-300 border border-rose-700 font-mono text-xs animate-bounce shadow-lg">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Barge-in Cutoff: <strong>{latestBargeIn.latency_ms}ms</strong></span>
            </div>
          )}
        </div>

        {/* Interactive Controls */}
        <div className="flex items-center space-x-4">
          {!isConnected ? (
            <button
              onClick={onConnect}
              disabled={connectionState === 'connecting'}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white font-semibold flex items-center space-x-2 shadow-lg shadow-cyan-500/25 transition-all transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50"
            >
              <Mic className="w-4 h-4" />
              <span>{connectionState === 'connecting' ? 'Establishing WebRTC...' : 'Start Conversation'}</span>
            </button>
          ) : (
            <>
              <button
                onClick={onDisconnect}
                className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-medium flex items-center space-x-2 transition-colors"
              >
                <MicOff className="w-4 h-4 text-rose-400" />
                <span>Disconnect</span>
              </button>

              <button
                onClick={onInterrupt}
                disabled={sessionState !== 'ai_speaking'}
                className="px-5 py-2.5 rounded-xl bg-rose-600/90 hover:bg-rose-500 text-white font-semibold flex items-center space-x-2 shadow-lg shadow-rose-600/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                title="Trigger immediate barge-in interruption"
              >
                <Hand className="w-4 h-4" />
                <span>Barge In (Interrupt)</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
