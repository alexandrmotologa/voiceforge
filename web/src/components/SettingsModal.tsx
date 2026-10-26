import React, { useState } from 'react';
import { X, Sliders, Wrench, CheckCircle2, Gauge } from 'lucide-react';
import { SessionConfig } from '../types';
import { AudioDeviceSelector } from './AudioDeviceSelector';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: SessionConfig;
  onSaveConfig: (newConfig: SessionConfig) => void;
  selectedAudioDeviceId?: string;
  onSelectAudioDevice: (devId: string) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  config,
  onSaveConfig,
  selectedAudioDeviceId,
  onSelectAudioDevice
}) => {
  const [formConfig, setFormConfig] = useState<SessionConfig>(config);
  const [activeTab, setActiveTab] = useState<'engine' | 'persona' | 'tools'>('engine');

  // Custom tool form state
  const [toolName, setToolName] = useState('');
  const [toolDesc, setToolDesc] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [toolFiller, setToolFiller] = useState('');
  const [toolRegisterSuccess, setToolRegisterSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveConfig(formConfig);
    onClose();
  };

  const handlePersonaSelect = (presetKey: string) => {
    if (presetKey === 'fast_copilot') {
      setFormConfig({
        ...formConfig,
        speech_rate: 1.25,
        stt_provider: 'fallback',
        llm_provider: 'fallback',
        tts_provider: 'native',
        system_prompt: 'You are an ultra-fast voice copilot. Give one-sentence punchy answers.'
      });
    } else if (presetKey === 'cloud_speed') {
      setFormConfig({
        ...formConfig,
        speech_rate: 1.1,
        stt_provider: 'deepgram',
        llm_provider: 'anthropic',
        tts_provider: 'cartesia',
        system_prompt: 'You are a high-speed conversational AI voice assistant.'
      });
    } else if (presetKey === 'local_offline') {
      setFormConfig({
        ...formConfig,
        speech_rate: 1.0,
        stt_provider: 'whisper_local',
        llm_provider: 'ollama',
        tts_provider: 'native',
        system_prompt: 'You are a private offline voice assistant operating on local hardware.'
      });
    }
  };

  const handleRegisterTool = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!toolName || !webhookUrl) return;

    try {
      const res = await fetch('/api/tools/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: toolName.trim(),
          description: toolDesc.trim() || `External webhook tool for ${toolName}`,
          webhook_url: webhookUrl.trim(),
          filler: toolFiller.trim() || undefined
        })
      });

      if (res.ok) {
        setToolRegisterSuccess(true);
        setToolName('');
        setToolDesc('');
        setWebhookUrl('');
        setToolFiller('');
        setTimeout(() => setToolRegisterSuccess(false), 3000);
      }
    } catch (err) {
      console.error('Failed to register tool:', err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in font-sans">
      <div className="w-full max-w-xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <h3 className="font-bold text-base text-slate-100">Studio & Engine Settings</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-2 border-b border-slate-800/80 pb-2 font-mono text-xs">
          <button
            onClick={() => setActiveTab('engine')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-colors ${
              activeTab === 'engine' ? 'bg-cyan-950 text-cyan-400 border border-cyan-800' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Pipeline & Audio
          </button>
          <button
            onClick={() => setActiveTab('persona')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-colors ${
              activeTab === 'persona' ? 'bg-indigo-950 text-indigo-400 border border-indigo-800' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Persona Presets
          </button>
          <button
            onClick={() => setActiveTab('tools')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-colors ${
              activeTab === 'tools' ? 'bg-purple-950 text-purple-400 border border-purple-800' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Custom Tools
          </button>
        </div>

        {activeTab === 'engine' && (
          <div className="space-y-4 font-mono text-xs">
            {/* Microphone Selection & Live VU meter */}
            <AudioDeviceSelector
              selectedDeviceId={selectedAudioDeviceId}
              onDeviceSelect={onSelectAudioDevice}
            />

            {/* STT Selection */}
            <div className="space-y-1.5">
              <label className="text-slate-300 font-semibold block">Speech-to-Text (STT) Provider</label>
              <select
                value={formConfig.stt_provider}
                onChange={(e) => setFormConfig({ ...formConfig, stt_provider: e.target.value as any })}
                className="w-full p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="fallback">Fallback (Built-in Local Acoustic - No Key)</option>
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
                <option value="native">Native Local PCM (Instant 50ms - Zero Cost)</option>
                <option value="cartesia">Cartesia Sonic (Sub-90ms First Byte)</option>
                <option value="elevenlabs">ElevenLabs Turbo v2.5</option>
              </select>
            </div>

            {/* Speech Rate Slider */}
            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between">
                <label className="text-slate-300 font-semibold flex items-center space-x-1.5">
                  <Gauge className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Voice Speech Rate (Speed Multiplier)</span>
                </label>
                <span className="text-cyan-400 font-bold">{formConfig.speech_rate || 1.0}x</span>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.5"
                step="0.05"
                value={formConfig.speech_rate || 1.0}
                onChange={(e) => setFormConfig({ ...formConfig, speech_rate: parseFloat(e.target.value) })}
                className="w-full accent-cyan-500"
              />
            </div>

            {/* VAD Sensitivity Threshold Slider */}
            <div className="space-y-1.5 pt-1">
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
            </div>
          </div>
        )}

        {activeTab === 'persona' && (
          <div className="space-y-4 font-mono text-xs">
            <p className="text-slate-400 font-sans">
              Choose a pre-tuned personality configuration for your voice agent:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => handlePersonaSelect('fast_copilot')}
                className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-cyan-500 text-left space-y-1 transition-all"
              >
                <div className="font-bold text-cyan-400">Ultra-Fast Voice Copilot</div>
                <div className="text-[11px] text-slate-400 font-sans">1.25x voice rate, local offline processing, punchy 1-sentence answers.</div>
              </button>

              <button
                type="button"
                onClick={() => handlePersonaSelect('cloud_speed')}
                className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500 text-left space-y-1 transition-all"
              >
                <div className="font-bold text-indigo-400">Cloud Real-Time (&lt;450ms)</div>
                <div className="text-[11px] text-slate-400 font-sans">Deepgram + Claude 3.5 Sonnet + Cartesia Sonic with lowest latency.</div>
              </button>

              <button
                type="button"
                onClick={() => handlePersonaSelect('local_offline')}
                className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-emerald-500 text-left space-y-1 transition-all"
              >
                <div className="font-bold text-emerald-400">100% Private Offline ($0)</div>
                <div className="text-[11px] text-slate-400 font-sans">Whisper Local + Ollama Llama 3 + Native PCM, zero data egress.</div>
              </button>
            </div>

            <div className="space-y-1.5 pt-2">
              <label className="text-slate-300 font-semibold block">Conversational System Prompt</label>
              <textarea
                rows={4}
                value={formConfig.system_prompt || ''}
                onChange={(e) => setFormConfig({ ...formConfig, system_prompt: e.target.value })}
                className="w-full p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono text-xs"
              />
            </div>
          </div>
        )}

        {activeTab === 'tools' && (
          <form onSubmit={handleRegisterTool} className="space-y-3 font-mono text-xs">
            <p className="text-slate-400 font-sans">
              Register an external webhook HTTP endpoint as a callable tool in runtime:
            </p>

            {toolRegisterSuccess && (
              <div className="p-3 rounded-lg bg-emerald-950/80 border border-emerald-800 text-emerald-300 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Tool registered into active registry successfully!</span>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-slate-300 font-semibold">Tool Identifier Name</label>
              <input
                type="text"
                placeholder="e.g. check_order_status"
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                className="w-full p-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-semibold">Description for LLM</label>
              <input
                type="text"
                placeholder="e.g. Query order status by order ID"
                value={toolDesc}
                onChange={(e) => setToolDesc(e.target.value)}
                className="w-full p-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-semibold">Webhook URL</label>
              <input
                type="url"
                placeholder="https://api.example.com/webhook"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="w-full p-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-semibold">Spoken Vocal Filler Phrase</label>
              <input
                type="text"
                placeholder="e.g. Checking your order right now."
                value={toolFiller}
                onChange={(e) => setToolFiller(e.target.value)}
                className="w-full p-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>

            <button
              type="submit"
              disabled={!toolName || !webhookUrl}
              className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold disabled:opacity-40 transition-colors shadow-md flex items-center space-x-1.5"
            >
              <Wrench className="w-3.5 h-3.5" />
              <span>Register Tool in Engine</span>
            </button>
          </form>
        )}

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
