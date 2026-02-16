import { useState, useEffect } from 'react';
import OpinionForm from './components/OpinionForm';
import ResultCard from './components/ResultCard';
import Constellation from './components/Constellation';
import { fetchCurrentQuestion, submitOpinion, fetchVisualization } from './api';

function App() {
  const [question, setQuestion] = useState(null);
  const [result, setResult] = useState(null);
  const [visData, setVisData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCurrentQuestion()
      .then(setQuestion)
      .catch(() => setError('Could not load question. Is the API running?'));

    fetchVisualization()
      .then(setVisData)
      .catch(() => {}); // Silently fail — no opinions yet is fine
  }, []);

  const handleSubmit = async (text, region) => {
    setLoading(true);
    setError(null);
    try {
      const res = await submitOpinion(text, region);
      setResult(res);
      // Refresh visualization
      const vis = await fetchVisualization();
      setVisData(vis);
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

      {/* Constellation visualization */}
      <Constellation
        points={visData?.points || []}
        highlightHash={result?.hash}
      />

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
