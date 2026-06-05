import { Search, ArrowUpLeft } from 'lucide-react';
import type { Suggestion } from '../../types';

type Props = {
  query: string;
  suggestions: Suggestion[];
  onFill: (text: string) => void;
  onSubmit: (text: string) => void;
};

function highlightMatch(text: string, query: string) {
  if (!query) return <span>{text}</span>;
  const ql = query.toLowerCase();
  const tl = text.toLowerCase();
  const idx = tl.indexOf(ql);
  if (idx === 0) {
    return (
      <>
        <strong style={{ fontWeight: 500 }}>{text.slice(0, query.length)}</strong>
        <span>{text.slice(query.length)}</span>
      </>
    );
  }
  return <span>{text}</span>;
}

export default function AutosuggestPanel({ query, suggestions, onFill, onSubmit }: Props) {
  if (!suggestions.length) return null;

  return (
    <div style={{ background: 'white', flex: 1 }}>
      {suggestions.map((s, i) => (
        <button
          key={`${s.text}-${i}`}
          className="w-full flex items-center gap-3 px-4 py-3.5 text-left"
          style={{
            borderBottom: i < suggestions.length - 1 ? '1px solid rgba(0,0,0,0.06)' : undefined,
            background: 'none',
            cursor: 'pointer',
          }}
          onClick={() => onSubmit(s.text)}
        >
          <Search size={15} color="#9ca3af" style={{ flexShrink: 0 }} />

          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-700 leading-snug">
              {highlightMatch(s.text, query)}
            </p>
            {s.context && (
              <p className="text-xs mt-0.5" style={{ color: '#62C8DF' }}>
                {s.context}
              </p>
            )}
          </div>

          <button
            onClick={e => {
              e.stopPropagation();
              onSubmit(s.text);
            }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, flexShrink: 0 }}
          >
            <ArrowUpLeft size={16} color="#9ca3af" />
          </button>
        </button>
      ))}
    </div>
  );
}
