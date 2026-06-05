import { useState } from 'react';

const STORAGE_KEY = 'marrow_recent_searches';
const MAX_RECENT = 5;

export const FALLBACK_SEARCHES = [
  'Cardiac cycle',
  'Anti-TB drugs',
  'Renal physiology',
  'MI management',
];

function readFromStorage(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed as string[];
    }
  } catch {}
  return [];
}

function writeToStorage(searches: string[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(searches));
  } catch {}
}

export function useRecentSearches() {
  const [saved, setSaved] = useState<string[]>(readFromStorage);

  const isFallback = saved.length === 0;
  const displayed = isFallback ? FALLBACK_SEARCHES : saved;

  function saveSearch(query: string) {
    const q = query.trim();
    if (!q) return;
    setSaved(prev => {
      const deduped = [q, ...prev.filter(s => s.toLowerCase() !== q.toLowerCase())];
      const next = deduped.slice(0, MAX_RECENT);
      writeToStorage(next);
      return next;
    });
  }

  function removeSearch(query: string) {
    setSaved(prev => {
      const next = prev.filter(s => s !== query);
      writeToStorage(next);
      return next;
    });
  }

  return { displayed, isFallback, saveSearch, removeSearch };
}
