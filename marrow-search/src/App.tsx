import { useState } from 'react';
import MobileFrame from './components/layout/MobileFrame';
import BottomNav from './components/layout/BottomNav';
import HomeTab from './components/tabs/HomeTab';
import QBankTab from './components/tabs/QBankTab';
import TestsTab from './components/tabs/TestsTab';
import VideosTab from './components/tabs/VideosTab';
import SearchExperience from './components/search/SearchExperience';
import VideoPage from './components/video/VideoPage';
import type { TabId, SearchResult } from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('home');
  const [searchOpen, setSearchOpen] = useState(false);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);

  const openSearch = () => setSearchOpen(true);
  const closeSearch = () => setSearchOpen(false);

  const tabScreen = {
    home: <HomeTab onSearchOpen={openSearch} />,
    qbank: <QBankTab onSearchOpen={openSearch} />,
    tests: <TestsTab onSearchOpen={openSearch} />,
    videos: <VideosTab onSearchOpen={openSearch} />,
  }[activeTab];

  return (
    <MobileFrame>
      {selectedResult !== null ? (
        <VideoPage
          result={selectedResult}
          onBack={() => setSelectedResult(null)}
          autoOpenNotes={selectedResult.type === 'note'}
          initialNotesPage={selectedResult.type === 'note' ? selectedResult.page_no : undefined}
        />
      ) : searchOpen ? (
        <SearchExperience
          onClose={closeSearch}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onResultClick={result => setSelectedResult(result)}
        />
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
            {tabScreen}
          </div>
          <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </>
      )}
    </MobileFrame>
  );
}
