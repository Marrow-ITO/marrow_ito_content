import { Menu, Bookmark, Search } from 'lucide-react';

type Props = {
  title?: string;
  showLogo?: boolean;
  onSearchOpen: () => void;
};

export default function TabHeader({ title, showLogo, onSearchOpen }: Props) {
  return (
    <div
      className="flex items-center px-4 py-3 gap-3"
      style={{ background: '#62C8DF', flexShrink: 0, minHeight: 56 }}
    >
      <Menu size={22} color="white" />
      <div className="flex-1">
        {showLogo ? (
          <div className="flex items-center gap-1.5">
            <span className="text-white font-medium text-lg">Marrow</span>
            <span
              className="text-xs px-1.5 py-0.5 rounded font-medium"
              style={{ background: '#F9A825', color: '#0F6E56' }}
            >
              PRO
            </span>
          </div>
        ) : (
          <span className="text-white font-medium text-base">{title}</span>
        )}
      </div>
      {showLogo && <Bookmark size={20} color="white" />}
      <button
        onClick={onSearchOpen}
        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
      >
        <Search size={20} color="white" />
      </button>
    </div>
  );
}
