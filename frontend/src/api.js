const BASE = '/api';

export async function fetchCurrentQuestion() {
  const res = await fetch(`${BASE}/question/current`);
  if (!res.ok) throw new Error('No active question');
  return res.json();
}

export async function submitOpinion(text, region) {
  const res = await fetch(`${BASE}/opinion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, region }),
  });
  if (!res.ok) throw new Error('Failed to submit opinion');
  return res.json();
}

export async function fetchVisualization() {
  const res = await fetch(`${BASE}/opinions/current`);
  if (!res.ok) throw new Error('Failed to fetch opinions');
  return res.json();
}

export async function fetchOpinion(hash) {
  const res = await fetch(`${BASE}/opinion/${hash}`);
  if (!res.ok) throw new Error('Opinion not found');
  return res.json();
}

export async function fetchSummary() {
  const res = await fetch(`${BASE}/opinions/current/summary`);
  if (!res.ok) throw new Error('No summary available');
  return res.json();
}
