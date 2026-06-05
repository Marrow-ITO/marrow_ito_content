import type { SearchTab } from '../../hooks/useSearch';

type Props = {
  activeTab: SearchTab;
  onTabChange: (tab: SearchTab) => void;
};

const TABS: { id: SearchTab; label: string }[] = [
  { id: 'all',    label: 'All' },
  { id: 'videos', label: 'Videos' },
  { id: 'notes',  label: 'Notes' },
  { id: 'qbank',  label: 'QBank' },
  { id: 'tests',  label: 'Tests' },
  { id: 'pearls', label: 'Pearls' },
];

export default function TabStrip({ activeTab, onTabChange }: Props) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        overflowX: 'auto',
        paddingBottom: 2,
        scrollbarWidth: 'none',
        flexShrink: 0,
      }}
    >
      {TABS.map(t => {
        const active = t.id === activeTab;
        return (
          <button
            key={t.id}
            onClick={() => onTabChange(t.id)}
            style={{
              flexShrink: 0,
              padding: '5px 14px',
              borderRadius: 999,
              fontSize: 13,
              fontWeight: active ? 500 : 400,
              cursor: 'pointer',
              border: active ? 'none' : '1px solid rgba(0,0,0,0.15)',
              background: active ? '#1f2937' : 'white',
              color: active ? 'white' : '#6b7280',
              transition: 'background 0.15s, color 0.15s',
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
