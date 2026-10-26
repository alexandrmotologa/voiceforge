import React, { useState, useEffect, useRef } from 'react';
import { Mic } from 'lucide-react';

interface AudioDeviceSelectorProps {
  onDeviceSelect: (deviceId: string) => void;
  selectedDeviceId?: string;
}

export const AudioDeviceSelector: React.FC<AudioDeviceSelectorProps> = ({
  onDeviceSelect,
  selectedDeviceId
}) => {
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [currentDeviceId, setCurrentDeviceId] = useState<string>(selectedDeviceId || '');
  const [isTesting, setIsTesting] = useState(false);
  const [testVolume, setTestVolume] = useState(0);

  const testStreamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    async function loadDevices() {
      try {
        // Request temporary mic permission to ensure full labels are returned
        const tempStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        tempStream.getTracks().forEach((t) => t.stop());

        const all = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = all.filter((d) => d.kind === 'audioinput');
        setDevices(audioInputs);
        if (audioInputs.length > 0 && !currentDeviceId) {
          setCurrentDeviceId(audioInputs[0].deviceId);
          onDeviceSelect(audioInputs[0].deviceId);
        }
      } catch (err) {
        console.debug('Could not enumerate audio devices:', err);
      }
    }
    loadDevices();
  }, [currentDeviceId, onDeviceSelect]);

  const handleDeviceChange = (devId: string) => {
    setCurrentDeviceId(devId);
    onDeviceSelect(devId);
    if (isTesting) {
      stopTest();
      startTest(devId);
    }
  };

  const startTest = async (devId?: string) => {
    try {
      setIsTesting(true);
      const targetId = devId || currentDeviceId;
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: targetId ? { exact: targetId } : undefined }
      });
      testStreamRef.current = stream;

      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioCtxRef.current = audioCtx;
      const src = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 128;
      src.connect(analyser);

      const buf = new Uint8Array(analyser.frequencyBinCount);

      const loop = () => {
        analyser.getByteFrequencyData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) sum += buf[i];
        const avg = sum / buf.length;
        setTestVolume(Math.min(100, (avg / 128) * 100));
        animFrameRef.current = requestAnimationFrame(loop);
      };
      loop();
    } catch (e) {
      console.error('Mic test error:', e);
      setIsTesting(false);
    }
  };

  const stopTest = () => {
    setIsTesting(false);
    setTestVolume(0);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (testStreamRef.current) {
      testStreamRef.current.getTracks().forEach((t) => t.stop());
      testStreamRef.current = null;
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close().catch(() => {});
    }
  };

  return (
    <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3 font-mono text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2 text-slate-300 font-semibold">
          <Mic className="w-4 h-4 text-cyan-400" />
          <span>Microphone Input Device</span>
        </div>
        <button
          onClick={isTesting ? stopTest : () => startTest()}
          className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-colors ${
            isTesting
              ? 'bg-rose-950 text-rose-300 border border-rose-800'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
          }`}
        >
          {isTesting ? 'Stop Mic Test' : 'Test Mic Level'}
        </button>
      </div>

      <select
        value={currentDeviceId}
        onChange={(e) => handleDeviceChange(e.target.value)}
        className="w-full p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 text-xs"
      >
        {devices.map((d, i) => (
          <option key={d.deviceId || i} value={d.deviceId}>
            {d.label || `Microphone ${i + 1}`}
          </option>
        ))}
      </select>

      {/* Live VU Meter during test */}
      {isTesting && (
        <div className="space-y-1 pt-1">
          <div className="flex justify-between text-[11px] text-slate-400">
            <span>Input Level</span>
            <span className={testVolume > 80 ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
              {Math.round(testVolume)}%
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              style={{ width: `${testVolume}%` }}
              className={`h-full transition-all duration-75 ${
                testVolume > 85 ? 'bg-rose-500' : testVolume > 40 ? 'bg-emerald-400' : 'bg-cyan-500'
              }`}
            />
          </div>
        </div>
      )}
    </div>
  );
};
