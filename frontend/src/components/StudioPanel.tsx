import { useState, useRef, useEffect } from "react";
import {
  Wand2, Play, Pause, Download, RefreshCw, AlertCircle, Gauge,
} from "lucide-react";
import type { Voice } from "../types";
import { generateSpeech } from "../api";

interface Props {
  voices: Voice[];
}

export default function StudioPanel({ voices }: Props) {
  const [text, setText]           = useState("");
  const [voiceId, setVoiceId]     = useState(voices[0]?.id ?? "af_heart");
  const [speed, setSpeed]         = useState(1.0);
  const [generating, setGenerating] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [audioUrl, setAudioUrl]   = useState<string | null>(null);
  const [playing, setPlaying]     = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (voices.length > 0 && !voices.find(v => v.id === voiceId)) {
      setVoiceId(voices[0].id);
    }
  }, [voices]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onEnd = () => setPlaying(false);
    audio.addEventListener("ended", onEnd);
    return () => audio.removeEventListener("ended", onEnd);
  }, [audioUrl]);

  const generate = async () => {
    if (!text.trim() || !voiceId) return;
    setGenerating(true);
    setError(null);
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
    setPlaying(false);
    try {
      const blob = await generateSpeech(text.trim(), voiceId, speed);
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      setTimeout(() => {
        audioRef.current?.play().then(() => setPlaying(true)).catch(() => {});
      }, 100);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const togglePlay = () => {
    const a = audioRef.current;
    if (!a) return;
    if (playing) { a.pause(); setPlaying(false); }
    else { a.play(); setPlaying(true); }
  };

  const download = () => {
    if (!audioUrl) return;
    const a = document.createElement("a");
    a.href = audioUrl;
    a.download = "speech.wav";
    a.click();
  };

  // Group voices by accent
  const american = voices.filter(v => v.accent === "American");
  const british  = voices.filter(v => v.accent === "British");

  const VoiceCard = ({ v }: { v: Voice }) => (
    <button
      key={v.id}
      onClick={() => setVoiceId(v.id)}
      className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-left transition-all ${
        voiceId === v.id
          ? "border-accent bg-accent/10 text-white"
          : "border-surface-4 bg-surface-2 text-gray-400 hover:border-surface-4 hover:text-gray-200 hover:bg-surface-3"
      }`}
    >
      <span className="text-lg">{v.gender === "F" ? "👩" : "👨"}</span>
      <div className="min-w-0">
        <p className="text-sm font-medium leading-tight truncate">{v.name}</p>
        <p className="text-xs opacity-60 leading-tight">{v.accent}</p>
      </div>
      {voiceId === v.id && (
        <span className="ml-auto w-2 h-2 rounded-full bg-accent shrink-0" />
      )}
    </button>
  );

  const charCount = text.length;
  const maxChars  = 3000;

  return (
    <div className="space-y-5 animate-fade-in">

      {/* Voice picker */}
      <div className="card space-y-3">
        <h2 className="font-semibold text-white text-sm uppercase tracking-wide opacity-60">Voice</h2>

        {american.length > 0 && (
          <div>
            <p className="text-xs text-gray-600 mb-2">🇺🇸 American English</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {american.map(v => <VoiceCard key={v.id} v={v} />)}
            </div>
          </div>
        )}
        {british.length > 0 && (
          <div>
            <p className="text-xs text-gray-600 mb-2">🇬🇧 British English</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {british.map(v => <VoiceCard key={v.id} v={v} />)}
            </div>
          </div>
        )}
      </div>

      {/* Speed */}
      <div className="card">
        <label className="label flex items-center justify-between mb-2">
          <span className="flex items-center gap-1"><Gauge className="w-3 h-3" /> Speed</span>
          <span className="text-accent-light font-mono">{speed.toFixed(2)}×</span>
        </label>
        <input
          type="range" min={0.5} max={2.0} step={0.05}
          value={speed}
          onChange={e => setSpeed(parseFloat(e.target.value))}
          className="w-full h-2 bg-surface-3 rounded-full appearance-none cursor-pointer accent-accent"
        />
        <div className="flex justify-between text-xs text-gray-600 mt-1">
          <span>0.5×</span><span>1.0×</span><span>2.0×</span>
        </div>
      </div>

      {/* Text input */}
      <div className="card space-y-3">
        <div className="flex items-center justify-between">
          <label className="label mb-0 flex items-center gap-1">
            <Wand2 className="w-3 h-3" /> Text to speak
          </label>
          <span className={`text-xs font-mono ${charCount > maxChars * 0.9 ? "text-warning" : "text-gray-600"}`}>
            {charCount}/{maxChars}
          </span>
        </div>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          maxLength={maxChars}
          rows={5}
          placeholder="Type or paste text here…"
          className="input resize-none font-sans text-sm leading-relaxed"
          onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) generate(); }}
        />

        {error && (
          <div className="flex items-start gap-2 text-sm bg-danger/10 text-danger rounded-lg px-3 py-2">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <button
          onClick={generate}
          disabled={!text.trim() || generating}
          className="btn-primary w-full justify-center text-base py-3"
        >
          {generating
            ? <><RefreshCw className="w-5 h-5 animate-spin" /> Generating…</>
            : <><Wand2 className="w-5 h-5" /> Generate Speech</>}
        </button>
        <p className="text-xs text-gray-700 text-center">Ctrl+Enter to generate</p>
      </div>

      {/* Audio output */}
      {audioUrl && (
        <div className="card space-y-3 border-accent/30 animate-slide-up">
          <audio ref={audioRef} src={audioUrl} className="hidden" />
          <div className="flex items-center gap-3 bg-surface-2 rounded-xl px-4 py-3">
            <button
              onClick={togglePlay}
              className="w-10 h-10 rounded-full bg-accent hover:bg-accent-hover flex items-center justify-center text-white transition-colors shrink-0"
            >
              {playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
            </button>
            <div className="flex-1">
              <p className="text-sm font-medium text-white">speech.wav</p>
              <p className="text-xs text-gray-600">Ready · click to play</p>
            </div>
            <button onClick={download} className="btn-ghost text-xs">
              <Download className="w-4 h-4" /> Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
