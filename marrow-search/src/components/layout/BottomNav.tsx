import { Home, Search, FileText, Video } from 'lucide-react';
import type { TabId } from '../../types';

type Props = {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
};

const tabs: { id: TabId; label: string; Icon: typeof Home }[] = [
  { id: 'home', label: 'Home', Icon: Home },
  { id: 'qbank', label: 'QBank', Icon: Search },
  { id: 'tests', label: 'Tests', Icon: FileText },
  { id: 'videos', label: 'Videos', Icon: Video },
];

export default function BottomNav({ activeTab, onTabChange }: Props) {
  return (
    <div className="flex border-t border-black/10 bg-white" style={{ flexShrink: 0 }}>
      {tabs.map(({ id, label, Icon }) => {
        const active = activeTab === id;
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className="flex-1 flex flex-col items-center py-2 gap-0.5"
            style={{ background: 'none', border: 'none', cursor: 'pointer' }}
          >
            <Icon
              size={22}
              style={{ color: active ? '#62C8DF' : '#9ca3af' }}
            />
            <span
              className="text-xs"
              style={{
                color: active ? '#62C8DF' : '#9ca3af',
                fontWeight: active ? 500 : 400,
              }}
            >
              {label}
            </span>
            {active && (
              <div
                style={{
                  width: 32,
                  height: 2,
                  background: '#62C8DF',
                  borderRadius: 1,
                  marginTop: 1,
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
