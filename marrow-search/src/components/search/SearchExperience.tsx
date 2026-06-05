import { useEffect, useRef } from 'react';
import SearchBar from './SearchBar';
import PreSearchScreen from './PreSearchScreen';
import AutosuggestPanel from './AutosuggestPanel';
import ResultsScreen from './ResultsScreen';
import BottomNav from '../layout/BottomNav';
import { useSearch } from '../../hooks/useSearch';
import { useRecentSearches } from '../../hooks/useRecentSearches';
import type { SearchState } from '../../hooks/useSearch';
import type { TabId, SearchResult } from '../../types';

type Props = {
  onClose: () => void;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  onResultClick: (result: SearchResult) => void;
};

export default function SearchExperience({ onClose, activeTab, onTabChange, onResultClick }: Props) {
  const {
    query, state, suggestions, searchResult,
    activeTab: searchTab, setActiveTab: setSearchTab,
    setQuery, submitSearch,
  } = useSearch();

  const { displayed: recentSearches, isFallback, saveSearch, removeSearch } = useRecentSearches();

  // Save query to recent searches when a search completes (loading → results/no_results).
  const prevStateRef = useRef<SearchState>('idle');
  useEffect(() => {
    const prev = prevStateRef.current;
    prevStateRef.current = state;
    if (prev === 'loading' && (state === 'results' || state === 'no_results')) {
      if (query.trim()) saveSearch(query);
    }
  }, [state]); // intentionally omit query/saveSearch — values are read at effect time

  const isResults = state === 'results' || state === 'no_results';

  function handleTabChange(tab: TabId) {
    onTabChange(tab);
    onClose();
  }

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
        <SearchBar
          query={query}
          onQueryChange={setQuery}
          onBack={onClose}
          onSubmit={() => submitSearch()}
          variant="teal"
        />

        <div style={{ flex: 1, overflowY: 'auto', background: '#F7F7F5' }}>
          {state === 'idle' && (
            <PreSearchScreen
              onSearch={q => submitSearch(q)}
              recentSearches={recentSearches}
              isFallback={isFallback}
              onRemoveSearch={removeSearch}
            />
          )}

          {(state === 'typing' || state === 'suggesting') && (
            <AutosuggestPanel
              query={query}
              suggestions={suggestions}
              onFill={setQuery}
              onSubmit={q => submitSearch(q)}
            />
          )}

          {state === 'loading' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, gap: 12 }}>
              <div style={{
                width: 28, height: 28, border: '3px solid #E1F5EE', borderTopColor: '#5DCAA5',
                borderRadius: '50%', animation: 'spin 0.7s linear infinite',
              }} />
              <span style={{ color: '#9ca3af', fontSize: 13 }}>Searching…</span>
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          )}

          {state === 'error' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, gap: 8 }}>
              <p style={{ fontSize: 14, fontWeight: 500, color: '#374151' }}>Couldn't reach the server</p>
              <p style={{ fontSize: 12, color: '#9ca3af', textAlign: 'center' }}>Check your connection and try again.</p>
            </div>
          )}

          {isResults && searchResult && (
            <ResultsScreen
              searchResult={searchResult}
              query={query}
              activeTab={searchTab}
              onTabChange={setSearchTab}
              onSearch={q => submitSearch(q)}
              onResultClick={onResultClick}
            />
          )}
        </div>
      </div>

      <BottomNav activeTab={activeTab} onTabChange={handleTabChange} />
    </>
  );
}
