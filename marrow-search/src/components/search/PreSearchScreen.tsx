import { Clock, TrendingUp, X } from 'lucide-react';
import { TRENDING_TOPICS } from '../../data/trendingData';

type Props = {
  onSearch: (query: string) => void;
  recentSearches: string[];
  isFallback: boolean;
  onRemoveSearch: (query: string) => void;
};

function SectionLabel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 mb-3">
      <span
        className="text-xs font-medium whitespace-nowrap"
        style={{ color: '#9ca3af', letterSpacing: '0.06em' }}
      >
        {label}
      </span>
      <div className="flex-1 h-px" style={{ background: 'rgba(0,0,0,0.1)' }} />
    </div>
  );
}

export default function PreSearchScreen({ onSearch, recentSearches, isFallback, onRemoveSearch }: Props) {
  return (
    <div className="px-4 pt-5 pb-4" style={{ background: '#F7F7F5', minHeight: '100%' }}>
      <SectionLabel label="RECENT SEARCHES" />

      <div className="flex flex-wrap gap-2 mb-6">
        {recentSearches.map(s => (
          <div
            key={s}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              background: 'white',
              borderRadius: 999,
              border: '1px solid rgba(0,0,0,0.12)',
              overflow: 'hidden',
            }}
          >
            {/* Tap to search */}
            <button
              type="button"
              onClick={() => onSearch(s)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: isFallback ? '6px 12px' : '6px 8px 6px 12px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: 13,
                color: '#374151',
              }}
            >
              <Clock size={13} color="#9ca3af" />
              {s}
            </button>

            {/* Remove button — only for saved searches, not fallback */}
            {!isFallback && (
              <button
                type="button"
                onClick={() => onRemoveSearch(s)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '6px 10px 6px 2px',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#9ca3af',
                }}
              >
                <X size={11} />
              </button>
            )}
          </div>
        ))}
      </div>

      <SectionLabel label="TRENDING IN NEET-PG · THIS WEEK" />

      <div className="rounded-xl bg-white overflow-hidden" style={{ border: '1px solid rgba(0,0,0,0.08)' }}>
        {TRENDING_TOPICS.map((item, i) => (
          <button
            key={item}
            type="button"
            onClick={() => onSearch(item)}
            className="w-full flex items-center px-4 py-3.5 gap-4 text-left"
            style={{
              background: 'none',
              border: 'none',
              borderTop: i > 0 ? '1px solid rgba(0,0,0,0.06)' : undefined,
              cursor: 'pointer',
            }}
          >
            <span
              className="text-sm"
              style={{ color: '#d1d5db', fontVariantNumeric: 'tabular-nums', minWidth: 12 }}
            >
              {i + 1}
            </span>
            <span className="flex-1 text-sm" style={{ color: '#374151' }}>{item}</span>
            <TrendingUp size={14} style={{ color: '#62C8DF', flexShrink: 0 }} />
          </button>
        ))}
      </div>
    </div>
  );
}
