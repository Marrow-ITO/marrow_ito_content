import { useState, useEffect, useRef } from 'react';
import { apiClient } from '../lib/apiClient';
import type { SearchResponse, Suggestion } from '../types';

export type SearchState = 'idle' | 'typing' | 'suggesting' | 'loading' | 'results' | 'no_results' | 'error';
export type SearchTab = 'all' | 'videos' | 'qbank' | 'tests' | 'pearls' | 'notes';

export function useSearch() {
  const [query, setQueryRaw] = useState('');
  const [state, setState] = useState<SearchState>('idle');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [activeTab, setActiveTab] = useState<SearchTab>('all');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isSubmittingRef = useRef(false);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    // submitSearch sets this flag before calling setQueryRaw so we don't
    // override 'loading' state when the query changes as part of a submit.
    if (isSubmittingRef.current) {
      isSubmittingRef.current = false;
      return;
    }

    if (!query.trim()) {
      setState('idle');
      setSuggestions([]);
      return;
    }

    setState('typing');

    debounceRef.current = setTimeout(async () => {
      try {
        const res = await apiClient.getSuggestions(query);
        setSuggestions(res.suggestions);
        setState('suggesting');
      } catch {
        // Silently fall back — suggestions failing shouldn't block typing
        setState('typing');
      }
    }, 150);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  function setQuery(q: string) {
    if (state === 'results' || state === 'no_results' || state === 'error') {
      setSearchResult(null);
    }
    setQueryRaw(q);
  }

  async function submitSearch(q?: string) {
    const finalQuery = (q !== undefined ? q : query).trim();
    if (!finalQuery) return;
    if (q !== undefined) {
      isSubmittingRef.current = true;
      setQueryRaw(q);
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setState('loading');
    setSuggestions([]);
    try {
      const res = await apiClient.search(finalQuery);
      setSearchResult(res);
      setState(res.no_results ? 'no_results' : 'results');
    } catch {
      setState('error');
    }
  }

  function reset() {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setQueryRaw('');
    setState('idle');
    setSuggestions([]);
    setSearchResult(null);
    setActiveTab('all');
  }

  return {
    query,
    state,
    suggestions,
    searchResult,
    activeTab,
    setActiveTab,
    setQuery,
    submitSearch,
    reset,
  };
}
