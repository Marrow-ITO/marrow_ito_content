import InterpretationCard from './InterpretationCard';
import RecentUpdateCard from './RecentUpdateCard';
import TabStrip from './TabStrip';
import ResultGroup from './ResultGroup';
import NoResultsState from './NoResultsState';
import type { SearchResponse, SearchResult } from '../../types';
import type { SearchTab } from '../../hooks/useSearch';

type Props = {
  searchResult: SearchResponse;
  query: string;
  activeTab: SearchTab;
  onTabChange: (tab: SearchTab) => void;
  onSearch: (q: string) => void;
  onResultClick: (result: SearchResult) => void;
};

type Group = { label: string; types: SearchResult['type'][]; tab: SearchTab | null };

const GROUP_ORDER: Group[] = [
  { label: 'VIDEOS',        types: ['video', 'timestamp'], tab: 'videos' },
  { label: 'NOTES',         types: ['note'],               tab: 'notes'  },
  { label: 'QBANK',         types: ['qbank'],              tab: 'qbank'  },
  { label: 'TESTS',         types: ['module'],             tab: 'tests'  },
  { label: 'PEARLS',        types: ['pearl'],              tab: 'pearls' },
  { label: 'CLINICAL CASES',types: ['clinical_q'],         tab: null     },
];

function filterByTab(results: SearchResult[], tab: SearchTab): SearchResult[] {
  if (tab === 'all')     return results;
  if (tab === 'videos')  return results.filter(r => r.type === 'video' || r.type === 'timestamp');
  if (tab === 'notes')   return results.filter(r => r.type === 'note');
  if (tab === 'qbank')   return results.filter(r => r.type === 'qbank');
  if (tab === 'tests')   return results.filter(r => r.type === 'module');
  if (tab === 'pearls')  return results.filter(r => r.type === 'pearl');
  return results;
}

export default function ResultsScreen({ searchResult, query, activeTab, onTabChange, onSearch, onResultClick }: Props) {
  const { interpreted_as, related_concepts, no_results, suggestions, results } = searchResult;

  const recentUpdates = results.filter(r => r.type === 'recent_update');
  const latestUpdate = recentUpdates.length > 0
    ? [...recentUpdates].sort((a, b) =>
        (b.date_of_update ?? '').localeCompare(a.date_of_update ?? '')
      )[0]
    : null;

  const groupableResults = results.filter(r => r.type !== 'recent_update');
  const visibleResults = filterByTab(groupableResults, activeTab);
  const isAllTab = activeTab === 'all';

  return (
    <div style={{ padding: '12px 14px', background: '#F7F7F5', minHeight: '100%' }}>
      {interpreted_as && (
        <InterpretationCard
          query={query}
          interpretedAs={interpreted_as}
          relatedConcepts={related_concepts}
          onChipClick={onSearch}
        />
      )}

      {latestUpdate && <RecentUpdateCard result={latestUpdate} />}

      <div style={{ marginBottom: 14 }}>
        <TabStrip activeTab={activeTab} onTabChange={onTabChange} />
      </div>

      {(no_results || groupableResults.length === 0) ? (
        <NoResultsState query={query} suggestions={suggestions || []} onSearch={onSearch} />
      ) : (
        <div>
          {GROUP_ORDER.map(g => {
            const group = visibleResults.filter(r => (g.types as string[]).includes(r.type));
            return (
              <ResultGroup
                key={g.label}
                label={g.label}
                results={group}
                isAllTab={isAllTab}
                onExpandAll={g.tab ? () => onTabChange(g.tab!) : undefined}
                onResultClick={onResultClick}
              />
            );
          })}

          {visibleResults.length === 0 && (
            <p style={{ textAlign: 'center', color: '#9ca3af', fontSize: 13, padding: '32px 0' }}>
              No results in this category
            </p>
          )}
        </div>
      )}
    </div>
  );
}
