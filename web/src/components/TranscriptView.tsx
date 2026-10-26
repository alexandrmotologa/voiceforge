import React, { useEffect, useRef } from 'react';
import { User, Bot, ShieldAlert, Clock } from 'lucide-react';
import { TranscriptMessage, ToolCallEvent } from '../types';

interface TranscriptViewProps {
  transcripts: TranscriptMessage[];
  toolCalls: ToolCallEvent[];
}

export const TranscriptView: React.FC<TranscriptViewProps> = ({ transcripts, toolCalls }) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcripts, toolCalls]);

  return (
    <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 flex flex-col h-[480px]">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <h3 className="font-semibold text-sm text-slate-200">Live Dialogue Transcript</h3>
        <span className="text-xs font-mono text-slate-500">{transcripts.length} messages</span>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 pr-2 font-sans">
        {transcripts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 font-mono text-xs space-y-2">
            <Clock className="w-6 h-6 text-slate-600" />
            <p>No conversation yet. Connect and speak to begin.</p>
          </div>
        ) : (
          transcripts.map((msg) => {
            const isUser = msg.speaker === 'user';
            return (
              <div
                key={msg.id}
                className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}
              >
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                  isUser
                    ? 'bg-emerald-600/30 text-emerald-400 border border-emerald-500/40'
                    : 'bg-indigo-600/30 text-indigo-400 border border-indigo-500/40'
                }`}>
                  {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                {/* Message Bubble */}
                <div className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm ${
                  isUser
                    ? 'bg-emerald-950/40 border border-emerald-800/60 text-emerald-100 rounded-tr-none'
                    : 'bg-slate-800/80 border border-slate-700/60 text-slate-100 rounded-tl-none'
                }`}>
                  <p className="leading-relaxed">{msg.text}</p>

                  {/* Barge-In interruption badge */}
                  {msg.isInterrupted && (
                    <div className="mt-2 pt-2 border-t border-rose-900/60 flex items-center space-x-1.5 text-xs font-mono text-rose-400 font-semibold">
                      <ShieldAlert className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                      <span>Interrupted by user ({msg.interruptLatencyMs || 68}ms barge-in cutoff)</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
