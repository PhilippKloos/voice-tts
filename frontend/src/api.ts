import type { Voice } from "./types";

const BASE = "/api";

export async function fetchVoices(): Promise<Voice[]> {
  const res = await fetch(`${BASE}/voices`);
  if (!res.ok) throw new Error("Failed to fetch voices");
  const data = await res.json();
  return data.voices as Voice[];
}

export async function generateSpeech(
  text: string,
  voiceId: string,
  speed: number,
): Promise<Blob> {
  const form = new FormData();
  form.append("text", text);
  form.append("voice_id", voiceId);
  form.append("speed", String(speed));
  const res = await fetch(`${BASE}/tts`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "TTS failed" }));
    throw new Error(err.detail || "Speech generation failed");
  }
  return res.blob();
}
