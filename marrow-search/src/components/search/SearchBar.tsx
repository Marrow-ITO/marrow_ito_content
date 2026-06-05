import { ChevronLeft, Search, X } from 'lucide-react';

type Props = {
  query: string;
  onQueryChange: (q: string) => void;
  onBack: () => void;
  onSubmit: () => void;
  variant?: 'teal' | 'light';
};

export default function SearchBar({ query, onQueryChange, onBack, onSubmit, variant = 'teal' }: Props) {
  const isLight = variant === 'light';
  return (
    <div
      className="flex items-center gap-3 px-3 py-3"
      style={{ background: isLight ? 'white' : '#62C8DF', flexShrink: 0, borderBottom: isLight ? '1px solid rgba(0,0,0,0.08)' : undefined }}
    >
      <button
        onClick={onBack}
        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, flexShrink: 0 }}
      >
        <ChevronLeft size={22} color={isLight ? '#374151' : 'white'} />
      </button>

      <div
        className="flex items-center gap-2 flex-1 px-3 py-2"
        style={{
          background: 'white',
          borderRadius: 999,
          minWidth: 0,
          border: isLight ? '1.5px solid rgba(0,0,0,0.2)' : undefined,
        }}
      >
        <Search size={15} color="#9ca3af" style={{ flexShrink: 0 }} />
        <input
          autoFocus
          type="text"
          value={query}
          onChange={e => onQueryChange(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') onSubmit(); }}
          placeholder="Search videos, QBank, tests…"
          style={{
            flex: 1,
            border: 'none',
            outline: 'none',
            fontSize: 14,
            color: '#1f2937',
            background: 'transparent',
            minWidth: 0,
          }}
        />
        {query.length > 0 && (
          <button
            type="button"
            onClick={() => onQueryChange('')}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, flexShrink: 0, display: 'flex' }}
          >
            <X size={15} color="#9ca3af" />
          </button>
        )}
      </div>
    </div>
  );
}
