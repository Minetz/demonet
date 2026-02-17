import { useState } from 'react';
import Fingerprint from './Fingerprint';

export default function ResultCard({ result }) {
  const [copied, setCopied] = useState(false);

  if (!result) return null;

  const shareUrl = `${window.location.origin}/s/${result.hash}`;

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-HTTPS contexts
      const input = document.createElement('input');
      input.value = shareUrl;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-8 space-y-6 animate-fade-in">
      {/* Your signature */}
      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)]">
        <div className="flex items-start gap-5">
          <Fingerprint hash={result.hash} size={100} className="shrink-0" />
          <div className="min-w-0 flex-1">
            <span className="text-xs text-[var(--color-text-dim)] tracking-wide uppercase">
              Your opinion signature
            </span>
            <p className="font-mono text-lg text-[var(--color-accent)] mt-1">
              #{result.hash}
            </p>
            <p className="mt-2 text-sm text-[var(--color-text-dim)] break-words">
              {result.anonymized_text}
            </p>
            {result.language && result.language !== 'en' && (
              <span className="inline-block mt-2 px-2 py-0.5 text-xs rounded bg-[var(--color-border)] text-[var(--color-text-dim)]">
                translated from {result.language}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Bridge — closest mind, furthest away */}
      {result.bridge && (
        <div className="p-6 rounded-2xl bg-gradient-to-br from-[#12121a] to-[#1a1025] border border-purple-900/30">
          <div className="flex items-start gap-4">
            <Fingerprint hash={result.bridge.hash} size={56} className="shrink-0 mt-1" />
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-purple-400 mb-2">
                Closest mind, furthest away
              </h3>
              <p className="text-[var(--color-text)]">
                &ldquo;{result.bridge.anonymized_text}&rdquo;
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className="font-mono text-xs text-[var(--color-text-dim)]">
                  #{result.bridge.hash}
                </span>
                {result.bridge.region && (
                  <span className="text-xs text-[var(--color-text-dim)]">
                    &middot; {result.bridge.region}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Nearest opinions */}
      {result.nearest?.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-[var(--color-text-dim)]">
            Similar minds ({result.nearest.length})
          </h3>
          {result.nearest.map((n) => (
            <div
              key={n.hash}
              className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]"
            >
              <div className="flex items-start gap-3">
                <Fingerprint hash={n.hash} size={36} className="shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-sm text-[var(--color-text)]">
                    &ldquo;{n.anonymized_text}&rdquo;
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="font-mono text-xs text-[var(--color-text-dim)]">
                      #{n.hash}
                    </span>
                    {n.region && (
                      <span className="text-xs text-[var(--color-text-dim)]">
                        &middot; {n.region}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Share */}
      <div className="text-center pt-4 space-y-3">
        <button
          onClick={copyLink}
          className="px-5 py-2.5 rounded-xl bg-[var(--color-accent)] text-white text-sm font-semibold hover:brightness-110 transition-all cursor-pointer"
        >
          {copied ? 'Link copied!' : 'Copy share link'}
        </button>
        <p className="text-[var(--color-text-dim)] text-xs font-mono">
          {shareUrl}
        </p>
      </div>
    </div>
  );
}
