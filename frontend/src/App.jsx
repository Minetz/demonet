import { useState, useEffect, useRef } from 'react';
import OpinionForm from './components/OpinionForm';
import ResultCard from './components/ResultCard';
import Constellation from './components/Constellation';
import { fetchCurrentQuestion, submitOpinion, fetchVisualization, fetchSummary } from './api';

function App() {
  const [question, setQuestion] = useState(null);
  const [result, setResult] = useState(null);
  const [visData, setVisData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  const refreshVis = () =>
    fetchVisualization()
      .then((data) => {
        setVisData(data);
        // Fetch summary once we have enough opinions
        if (data?.total_opinions >= 3) {
          fetchSummary().then(setSummary).catch(() => {});
        }
      })
      .catch(() => {});

  useEffect(() => {
    fetchCurrentQuestion()
      .then(setQuestion)
      .catch(() => setError('Could not load question. Is the API running?'));

    refreshVis();

    // Poll every 30 s for live updates
    pollRef.current = setInterval(refreshVis, 30_000);
    return () => clearInterval(pollRef.current);
  }, []);

  const handleSubmit = async (text, region) => {
    setLoading(true);
    setError(null);
    try {
      const res = await submitOpinion(text, region);
      setResult(res);
      await refreshVis();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12 md:py-20">
      {/* Header */}
      <header className="mb-12 text-center">
        <p className="text-xs tracking-[0.3em] uppercase text-[var(--color-text-dim)] mb-2">
          The World's Take
        </p>
      </header>

      {error && (
        <div className="w-full max-w-2xl mx-auto mb-6 p-4 rounded-xl bg-red-900/20 border border-red-800/30 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Main flow */}
      {!result ? (
        <OpinionForm
          question={question}
          onSubmit={handleSubmit}
          loading={loading}
        />
      ) : (
        <>
          <div className="text-center mb-8">
            <h1 className="text-2xl md:text-4xl font-bold mb-2 bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              {question?.text}
            </h1>
            <button
              onClick={() => setResult(null)}
              className="text-sm text-[var(--color-accent)] hover:underline cursor-pointer mt-2"
            >
              Share another take
            </button>
          </div>
          <ResultCard result={result} />
        </>
      )}

      {/* Opinion count */}
      {visData?.total_opinions > 0 && (
        <p className="text-xs text-[var(--color-text-dim)] mt-6 tracking-wide">
          {visData.total_opinions} {visData.total_opinions === 1 ? 'voice' : 'voices'} from around the world
        </p>
      )}

      {/* Constellation visualization */}
      <Constellation
        points={visData?.points || []}
        highlightHash={result?.hash}
      />

      {/* Global summary */}
      {summary && (
        <div className="w-full max-w-2xl mx-auto mt-6 p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)]">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-dim)] mb-3">
            What the world thinks
          </h3>
          <p className="text-sm text-[var(--color-text)] leading-relaxed">
            {summary.summary}
          </p>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-16 text-center text-xs text-[var(--color-text-dim)]">
        <p>Open source. Open protocol. Your identity is never stored.</p>
        <p className="mt-1">
          Sign your opinion. See the world's.
        </p>
      </footer>
    </div>
  );
}

export default App;
