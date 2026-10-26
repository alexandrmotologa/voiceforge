import React from 'react';
import { Wrench, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { ToolCallEvent } from '../types';

interface ToolMonitorProps {
  toolCalls: ToolCallEvent[];
}

export const ToolMonitor: React.FC<ToolMonitorProps> = ({ toolCalls }) => {
  return (
    <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 flex flex-col h-[480px]">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center space-x-2">
          <Wrench className="w-4 h-4 text-indigo-400" />
          <h3 className="font-semibold text-sm text-slate-200">Conversational Tool Runner</h3>
        </div>
        <span className="text-xs font-mono text-slate-500">{toolCalls.length} calls</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-2 font-mono text-xs">
        {toolCalls.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 space-y-2">
            <Sparkles className="w-6 h-6 text-slate-600" />
            <p className="font-medium text-slate-400">No tools invoked yet</p>
            <p className="max-w-xs text-slate-500 text-[11px]">
              Ask VoiceForge for current weather, calculations, local time, or system diagnostics to trigger function calling.
            </p>
          </div>
        ) : (
          toolCalls.map((call, idx) => (
            <div key={idx} className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800 font-bold">
                    {call.tool_name}
                  </span>
                  {call.duration_ms && (
                    <span className="text-[11px] text-slate-500">{call.duration_ms}ms</span>
                  )}
                </div>

                <div className="flex items-center space-x-1">
                  {call.status === 'executing' ? (
                    <span className="flex items-center space-x-1 text-amber-400 text-[11px]">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      <span>Executing</span>
                    </span>
                  ) : (
                    <span className="flex items-center space-x-1 text-emerald-400 text-[11px]">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Done</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Vocal Filler Spoken */}
              {call.filler_spoken && (
                <div className="text-[11px] text-slate-400 font-sans italic bg-slate-900/60 px-2.5 py-1.5 rounded-lg border border-slate-800/80">
                  <span className="font-semibold text-slate-300">Spoken Filler:</span> "{call.filler_spoken}"
                </div>
              )}

              {/* Result Preview */}
              {call.result && (
                <pre className="text-[11px] bg-slate-900/90 text-slate-300 p-2 rounded-lg overflow-x-auto border border-slate-800">
                  {JSON.stringify(call.result, null, 2)}
                </pre>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
