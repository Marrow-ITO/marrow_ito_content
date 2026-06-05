import TabHeader from '../layout/TabHeader';
import { TrendingUp, ChevronRight } from 'lucide-react';

type Props = { onSearchOpen: () => void };

type TestItem = {
  title: string;
  schedule: string;
  duration: string;
  mcqs: string;
  live?: boolean;
  highlight?: boolean;
};

const junTests: TestItem[] = [
  {
    title: 'Grand Test 17 – NEET Pattern',
    schedule: 'Live till 08 Jun - 14:00',
    duration: '210 mins',
    mcqs: '200 MCQs',
    live: true,
    highlight: true,
  },
  {
    title: 'INICET Recall – May 2026',
    schedule: 'Live on 24 Jun - 10:00',
    duration: '180 mins',
    mcqs: '200 MCQs',
  },
  {
    title: 'Subject Test – Pharmacology',
    schedule: 'Live on 14 Jun - 10:00',
    duration: '90 mins',
    mcqs: '100 MCQs',
  },
  {
    title: 'Mini Test – Clinical Scenarios 5',
    schedule: 'Live on 20 Jun - 10:00',
    duration: '60 mins',
    mcqs: '50 MCQs',
  },
];

const julTests: TestItem[] = [
  { title: 'Grand Test 18 – NEET Pattern', schedule: 'Live on 01 Jul - 10:00', duration: '210 mins', mcqs: '200 MCQs' },
  { title: 'Subject Test – Pathology', schedule: 'Live on 10 Jul - 10:00', duration: '90 mins', mcqs: '100 MCQs' },
  { title: 'Grand Test 19 – NEET Pattern', schedule: 'Live on 15 Jul - 10:00', duration: '210 mins', mcqs: '200 MCQs' },
  { title: 'Mini Test – Rapid Fire Round 3', schedule: 'Live on 18 Jul - 10:00', duration: '45 mins', mcqs: '50 MCQs' },
  { title: 'National NEET-PG Mock 2026', schedule: 'Live on 22 Jul - 10:00', duration: '240 mins', mcqs: '200 MCQs' },
];

const augTests: TestItem[] = [
  { title: 'Grand Test 20 – NEET Pattern', schedule: 'Live on 05 Aug - 10:00', duration: '210 mins', mcqs: '200 MCQs' },
  { title: 'INI-CET Mock Test – Aug', schedule: 'Live on 12 Aug - 10:00', duration: '180 mins', mcqs: '150 MCQs' },
  { title: 'Grand Test 21 – NEET Pattern', schedule: 'Live on 19 Aug - 10:00', duration: '210 mins', mcqs: '200 MCQs' },
  { title: 'FMGE Recall Mock', schedule: 'Live on 26 Aug - 10:00', duration: '150 mins', mcqs: '150 MCQs' },
];

function TestCard({ t }: { t: TestItem }) {
  return (
    <div
      className="rounded-xl p-3"
      style={{
        background: t.highlight ? '#FAEEDA' : 'white',
        border: '1px solid rgba(0,0,0,0.08)',
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          {t.live ? (
            <div className="w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0" style={{ background: '#e53e3e' }} />
          ) : (
            <div className="w-2.5 h-2.5 mt-1 flex-shrink-0" />
          )}
          <div>
            <p className="text-sm font-medium text-gray-700">{t.title}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              {t.schedule} · {t.duration} · {t.mcqs}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {t.live && (
            <span className="text-xs px-1.5 py-0.5 rounded font-medium text-white" style={{ background: '#e53e3e' }}>
              LIVE
            </span>
          )}
          <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: '#0F6E56', color: 'white' }}>
            PRO
          </span>
        </div>
      </div>
    </div>
  );
}

function MonthGroup({ label, tests }: { label: string; tests: TestItem[] }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <div className="h-px flex-1" style={{ background: 'rgba(0,0,0,0.1)' }} />
        <span className="text-xs text-gray-400 whitespace-nowrap">{label}</span>
        <div className="h-px flex-1" style={{ background: 'rgba(0,0,0,0.1)' }} />
      </div>
      <div className="space-y-2">
        {tests.map((t) => <TestCard key={t.title} t={t} />)}
      </div>
    </div>
  );
}

export default function TestsTab({ onSearchOpen }: Props) {
  return (
    <>
      <TabHeader title="Tests" onSearchOpen={onSearchOpen} />
      <div
        className="flex items-center px-4 gap-4"
        style={{ background: '#62C8DF', paddingBottom: 8 }}
      >
        {['Grand Tests', 'Mini Tests', 'Subject Tests'].map((t, i) => (
          <button
            key={t}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: i === 0 ? 'white' : 'rgba(255,255,255,0.65)',
              fontWeight: i === 0 ? 500 : 400,
              fontSize: 13,
              paddingBottom: 6,
              borderBottom: i === 0 ? '2px solid white' : '2px solid transparent',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto" style={{ background: '#F7F7F5' }}>
        <div className="p-4 space-y-3">
          <div
            className="rounded-xl bg-white p-3 flex items-center justify-between"
            style={{ border: '1px solid rgba(0,0,0,0.08)' }}
          >
            <div className="flex items-center gap-2">
              <TrendingUp size={18} style={{ color: '#62C8DF' }} />
              <span className="text-sm text-gray-600">Your overall progress in GTs</span>
            </div>
            <ChevronRight size={16} className="text-gray-300" />
          </div>

          <div className="flex items-center justify-between px-1">
            <span className="text-xs text-gray-400 uppercase tracking-wide">MAY</span>
            <span className="text-xs text-gray-400">YEAR 2025 – 26</span>
          </div>

          <MonthGroup label="JUN (Current Month)" tests={junTests} />
          <MonthGroup label="JUL (Upcoming Month)" tests={julTests} />
          <MonthGroup label="AUG (Future)" tests={augTests} />
        </div>
      </div>
    </>
  );
}
