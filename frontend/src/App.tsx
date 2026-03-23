import { useState, useEffect } from "react";
import { RefreshCw } from "lucide-react";
import { fetchVoices } from "./api";
import type { Voice } from "./types";
import StudioPanel from "./components/StudioPanel";
import Header from "./components/Header";

export default function App() {
  const [voices, setVoices]   = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const loadVoices = async () => {
    setLoading(true);
    setError(null);
    try {
      setVoices(await fetchVoices());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadVoices(); }, []);

  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <Header />

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-6 sm:px-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 gap-3 text-gray-500">
            <RefreshCw className="w-5 h-5 animate-spin" />
            <span>Connecting to backend…</span>
          </div>
        ) : error ? (
          <div className="card border-danger/40 bg-danger/5 text-center py-12">
            <p className="text-danger font-medium mb-2">Backend unreachable</p>
            <p className="text-sm text-gray-500 mb-4">{error}</p>
            <button onClick={loadVoices} className="btn-ghost text-xs">
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </button>
          </div>
        ) : (
          <StudioPanel voices={voices} />
        )}
      </main>

      <footer className="text-center text-xs text-gray-700 py-4 border-t border-surface-3">
        VoiceTTS · Powered by Piper TTS
      </footer>
    </div>
  );
}
