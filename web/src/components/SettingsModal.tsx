import React from 'react';
import { X, Sliders } from 'lucide-react';
import { SessionConfig } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: SessionConfig;
  onSaveConfig: (newConfig: SessionConfig) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  config,
  onSaveConfig
}) => {
  const [formConfig, setFormConfig] = React.useState<SessionConfig>(config);

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveConfig(formConfig);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in font-sans">
      <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <h3 className="font-bold text-base text-slate-100">Engine & Pipeline Settings</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4 font-mono text-xs">
          {/* STT Selection */}
          <div className="space-y-1.5">
            <label className="text-slate-300 font-semibold block">Speech-to-Text (STT) Provider</label>
            <select
              value={formConfig.stt_provider}
              onChange={(e) => setFormConfig({ ...formConfig, stt_provider: e.target.value as any })}
              className="w-full p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="fallback">Fallback (Built-in Local Acoustic - No API Key)</option>
              <option value="deepgram">Deepgram Nova-2 (Ultra-fast WebSocket &lt;110ms)</option>
              <option value="whisper_local">Whisper Local (faster-whisper CPU/GPU)</option>
            </select>
          </div>

          {/* LLM Selection */}
          <div className="space-y-1.5">
            <label className="text-slate-300 font-semibold block">Language Model (LLM) Engine</label>
            <select
              value={formConfig.llm_provider}
              onChange={(e) => setFormConfig({ ...formConfig, llm_provider: e.target.value as any })}
              className="w-full p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="fallback">Fallback (Built-in Local Rule & Tool Engine - No Key)</option>
              <option value="anthropic">Anthropic Claude 3.5 Sonnet (Streaming SSE)</option>
              <option value="openai">OpenAI GPT-4o-mini (Streaming SSE)</option>
              <option value="ollama">Ollama / vLLM (Local Endpoint localhost:11434)</option>
            </select>
          </div>

          {/* TTS Selection */}
          <div className="space-y-1.5">
            <label className="text-slate-300 font-semibold block">Text-to-Speech (TTS) Synthesizer</label>
            <select
              value={formConfig.tts_provider}
              onChange={(e) => setFormConfig({ ...formConfig, tts_provider: e.target.value as any })}
              className="w-full p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="native">Native Local PCM (Instant 50ms - Zero Cloud Cost)</option>
              <option value="cartesia">Cartesia Sonic (Sub-90ms First Byte)</option>
              <option value="elevenlabs">ElevenLabs Turbo v2.5</option>
            </select>
          </div>

          {/* VAD Sensitivity Threshold Slider */}
          <div className="space-y-1.5 pt-2">
            <div className="flex justify-between">
              <label className="text-slate-300 font-semibold">Silero VAD Sensitivity Threshold</label>
              <span className="text-cyan-400 font-bold">{formConfig.vad_threshold}</span>
            </div>
            <input
              type="range"
              min="0.2"
              max="0.8"
              step="0.05"
              value={formConfig.vad_threshold}
              onChange={(e) => setFormConfig({ ...formConfig, vad_threshold: parseFloat(e.target.value) })}
              className="w-full accent-cyan-500"
            />
            <p className="text-[11px] text-slate-500 font-sans">
              Lower threshold triggers speech faster; higher threshold prevents false positives in noisy environments.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-cyan-500/20"
          >
            Apply Changes
          </button>
        </div>
      </div>
    </div>
  );
};
