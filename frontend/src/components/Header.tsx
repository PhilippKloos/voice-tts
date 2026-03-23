export default function Header() {
  return (
    <header className="border-b border-surface-3 bg-surface-1 sticky top-0 z-20">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 flex items-center h-14 gap-3">
        <span className="text-xl">🎙️</span>
        <span className="font-bold text-white tracking-tight">VoiceTTS</span>
        <span className="badge bg-accent/20 text-accent-light">Beta</span>
      </div>
    </header>
  );
}
