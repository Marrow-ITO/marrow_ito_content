import { SearchX, TrendingUp } from 'lucide-react';
import { TRENDING_TOPICS } from '../../data/trendingData';

type Props = {
  query: string;
  suggestions: string[];
  onSearch: (q: string) => void;
};

export default function NoResultsState({ query, suggestions, onSearch }: Props) {
  return (
    <div style={{ paddingBottom: 24 }}>
      {/* Top: icon + message */}
      <div style={{ textAlign: 'center', padding: '32px 24px 24px' }}>
        <div
          style={{
            width: 60,
            height: 60,
            borderRadius: 30,
            background: '#f3f4f6',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
          }}
        >
          <SearchX size={28} color="#9ca3af" />
        </div>

        <p style={{ fontSize: 15, fontWeight: 500, color: '#374151', marginBottom: 6 }}>
          No results for "{query}"
        </p>
        <p style={{ fontSize: 13, color: '#9ca3af' }}>
          Try checking your spelling or using a broader term
        </p>
      </div>

      {/* Did you mean */}
      {suggestions.length > 0 && (
        <div style={{ padding: '0 16px 20px' }}>
          <p style={{ fontSize: 12, fontWeight: 500, color: '#6b7280', marginBottom: 10 }}>
            Did you mean?
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {suggestions.map(s => (
              <button
                key={s}
                type="button"
                onClick={() => onSearch(s)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: 13,
                  fontWeight: 500,
                  color: '#0F6E56',
                  background: '#E1F5EE',
                  border: '1px solid rgba(15,110,86,0.2)',
                  padding: '6px 14px',
                  borderRadius: 999,
                  cursor: 'pointer',
                }}
              >
                ↳ {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Divider */}
      <div style={{ height: 1, background: 'rgba(0,0,0,0.08)', margin: '0 16px 20px' }} />

      {/* Trending */}
      <div style={{ padding: '0 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <span
            style={{
              fontSize: 10,
              fontWeight: 500,
              color: '#9ca3af',
              letterSpacing: '0.07em',
              whiteSpace: 'nowrap',
            }}
          >
            TRENDING IN NEET-PG
          </span>
          <div style={{ flex: 1, height: 1, background: 'rgba(0,0,0,0.08)' }} />
        </div>

        <div
          style={{
            background: 'white',
            borderRadius: 12,
            border: '1px solid rgba(0,0,0,0.08)',
            overflow: 'hidden',
          }}
        >
          {TRENDING_TOPICS.map((item, i) => (
            <button
              key={item}
              type="button"
              onClick={() => onSearch(item)}
              style={{
                display: 'flex',
                alignItems: 'center',
                width: '100%',
                padding: '12px 16px',
                gap: 12,
                background: 'none',
                border: 'none',
                borderTop: i > 0 ? '1px solid rgba(0,0,0,0.06)' : undefined,
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <span style={{ fontSize: 13, color: '#d1d5db', minWidth: 14, fontVariantNumeric: 'tabular-nums' }}>
                {i + 1}
              </span>
              <span style={{ flex: 1, fontSize: 13, color: '#374151' }}>{item}</span>
              <TrendingUp size={14} style={{ color: '#62C8DF', flexShrink: 0 }} />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
