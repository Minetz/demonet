import { useState } from 'react';

export default function OpinionForm({ question, onSubmit, loading }) {
  const [text, setText] = useState('');
  const [region, setRegion] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    onSubmit(text.trim(), region.trim() || null);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl md:text-5xl font-bold mb-3 bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
          {question?.text || 'Loading...'}
        </h1>
        <p className="text-[var(--color-text-dim)] text-sm">
          One question. The whole planet answers. AI connects the dots.
        </p>
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Share your take... (any language)"
        rows={5}
        maxLength={5000}
        className="w-full p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] placeholder:text-[var(--color-text-dim)] resize-none focus:outline-none focus:border-[var(--color-accent)] focus:shadow-[0_0_20px_var(--color-accent-glow)] transition-all"
        disabled={loading}
      />

      <div className="flex items-center gap-3 mt-3">
        <input
          type="text"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          placeholder="Your region (optional, e.g. 'Brazil')"
          className="flex-1 p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] placeholder:text-[var(--color-text-dim)] text-sm focus:outline-none focus:border-[var(--color-accent)] transition-all"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="px-6 py-3 rounded-xl bg-[var(--color-accent)] text-white font-semibold hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer"
        >
          {loading ? 'Signing...' : 'Sign & Share'}
        </button>
      </div>

      <p className="text-[var(--color-text-dim)] text-xs mt-2">
        Your identity is anonymized. PII is stripped. Only your opinion travels.
      </p>
    </form>
  );
}
