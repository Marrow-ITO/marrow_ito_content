import ResultCard from './ResultCard';
import type { SearchResult } from '../../types';

type Props = {
  label: string;
  results: SearchResult[];
  isAllTab: boolean;
  onExpandAll?: () => void;
  onResultClick: (result: SearchResult) => void;
};

const TRUNCATE_AT = 3;

export default function ResultGroup({ label, results, isAllTab, onExpandAll, onResultClick }: Props) {
  if (!results.length) return null;

  const displayed = isAllTab ? results.slice(0, TRUNCATE_AT) : results;
  const hasMore = isAllTab && results.length > TRUNCATE_AT;

  return (
    <div style={{ marginBottom: 16 }}>
      {/* Section header — always shows total count */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span
          style={{
            fontSize: 10,
            fontWeight: 500,
            color: '#9ca3af',
            letterSpacing: '0.07em',
            whiteSpace: 'nowrap',
          }}
        >
          {label} · {results.length}
        </span>
        <div style={{ flex: 1, height: 1, background: 'rgba(0,0,0,0.08)' }} />
      </div>

      {/* Cards container */}
      <div
        style={{
          background: 'white',
          borderRadius: 12,
          border: '1px solid rgba(0,0,0,0.08)',
          overflow: 'hidden',
        }}
      >
        {displayed.map((r, i) => (
          <div
            key={r.id}
            style={{ borderTop: i > 0 ? '1px solid rgba(0,0,0,0.06)' : undefined }}
          >
            <ResultCard result={r} onResultClick={onResultClick} />
          </div>
        ))}

        {hasMore && (
          <button
            onClick={onExpandAll}
            style={{
              display: 'block',
              width: '100%',
              padding: '10px 14px',
              background: 'none',
              border: 'none',
              borderTop: '1px solid rgba(0,0,0,0.06)',
              cursor: 'pointer',
              fontSize: 12,
              color: '#62C8DF',
              textAlign: 'left',
              fontWeight: 500,
            }}
          >
            Expand all · {results.length} results →
          </button>
        )}
      </div>
    </div>
  );
}
