import TabHeader from '../layout/TabHeader';

type Props = { onSearchOpen: () => void };

export default function HomeTab({ onSearchOpen }: Props) {
  return (
    <>
      <TabHeader showLogo onSearchOpen={onSearchOpen} />
      <div
        className="flex-1 overflow-y-auto"
        style={{ background: '#F7F7F5' }}
      >
        <div
          className="flex flex-col items-center py-8"
          style={{ background: '#62C8DF' }}
        >
          <div
            className="flex items-center justify-center rounded-full"
            style={{
              width: 96,
              height: 96,
              border: '4px solid #9CCC65',
              background: 'rgba(255,255,255,0.15)',
            }}
          >
            <span className="text-white text-2xl font-medium">780</span>
          </div>
          <span className="text-white text-sm mt-2">Modules completed</span>
        </div>

        <div className="p-4 space-y-3">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Featured</p>
          <div
            className="rounded-xl p-4"
            style={{ background: '#FAEEDA', border: '1px solid rgba(0,0,0,0.08)' }}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center text-xl"
                style={{ background: '#F9A825' }}
              >
                G
              </div>
              <div>
                <p className="font-medium text-gray-800">Grand Test 17</p>
                <p className="text-xs text-gray-500">5 sections, 40 MCQs each</p>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-3 pt-3" style={{ borderTop: '1px solid rgba(0,0,0,0.08)' }}>
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center"
                style={{ background: '#62C8DF' }}
              >
                <span className="text-white text-xs">▶</span>
              </div>
              <span className="text-sm font-medium" style={{ color: '#0F6E56' }}>
                Live Now | NEET Pattern
              </span>
            </div>
          </div>

          <div className="rounded-xl bg-white p-4" style={{ border: '1px solid rgba(0,0,0,0.08)' }}>
            <p className="text-xs font-medium mb-2" style={{ color: '#62C8DF' }}>
              MCQ of the Day – NEET Pattern
            </p>
            <p className="text-sm text-gray-700 leading-relaxed">
              A pregnant woman came for routine antenatal screening. During prenatal testing, the fetus was suspected to have congenital adrenal hyperplasia. What is the drug of choice for treating the fetus in-utero?
            </p>
            <div className="mt-3 space-y-2">
              {['Dexamethasone', 'Betamethasone', 'Hydrocortisone', 'Prednisolone'].map((opt, i) => (
                <div
                  key={opt}
                  className="rounded-lg px-3 py-2 text-sm text-gray-700"
                  style={{ background: '#F7F7F5', border: '1px solid rgba(0,0,0,0.08)' }}
                >
                  {String.fromCharCode(65 + i)}) {opt}
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide pt-1">
            Suggested Tests of the Day
          </p>
          <div className="rounded-xl bg-white p-4" style={{ border: '1px solid rgba(0,0,0,0.08)' }}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center"
                  style={{ background: '#F9A825' }}
                >
                  <span className="text-white font-medium text-sm">M</span>
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <p className="text-sm text-gray-700">Clinical Mini Test 4 - Management Prot…</p>
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span
                      className="text-xs px-1.5 py-0.5 rounded font-medium text-white"
                      style={{ background: '#e53e3e' }}
                    >
                      ● LIVE
                    </span>
                    <span className="text-xs text-gray-400">Expires on 05 Jun - 10:00</span>
                  </div>
                </div>
              </div>
              <span className="text-xs text-gray-400">Pro</span>
            </div>
          </div>

          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide pt-1">Solve Next</p>
          <div className="rounded-xl bg-white p-3 flex items-center gap-3" style={{ border: '1px solid rgba(0,0,0,0.08)' }}>
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center text-lg flex-shrink-0"
              style={{ background: '#E6F1FB' }}
            >
              🏥
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 truncate">Natl Health Programmes II - NLEP, NTEP</p>
              <p className="text-xs text-gray-400">Community Medicine · ★ 4.6 · 24 MCQs</p>
            </div>
            <span className="text-gray-300">›</span>
          </div>

          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide pt-1">Watch Next</p>
          <div className="rounded-xl bg-white p-3 flex items-center gap-3" style={{ border: '1px solid rgba(0,0,0,0.08)' }}>
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center text-lg flex-shrink-0"
              style={{ background: '#E6F1FB' }}
            >
              ▶
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: '#378ADD' }}>Pharmacokinetics: Metabolism</p>
              <p className="text-xs text-gray-400">Pharmacology · ★ 4.6 · 38 min</p>
            </div>
            <span className="text-gray-300">›</span>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div
              className="rounded-xl p-4"
              style={{ background: '#F9A825' }}
            >
              <p className="text-white font-medium text-sm">Pearls</p>
              <p className="text-white text-2xl font-medium">2165</p>
              <p className="text-white text-xs opacity-80">pearls collected</p>
            </div>
            <div
              className="rounded-xl p-4"
              style={{ background: '#E8F5E9' }}
            >
              <p className="text-sm font-medium" style={{ color: '#0F6E56' }}>Magic Module</p>
              <p className="text-xs mt-1" style={{ color: '#0F6E56' }}>Module 13 LIVE now!</p>
            </div>
          </div>

          <div className="rounded-xl bg-white p-3" style={{ border: '1px solid rgba(0,0,0,0.08)' }}>
            <p className="text-sm text-gray-600">Recent Updates</p>
            <p className="text-xs text-gray-400 mt-0.5">Last updated: 3 June 2026</p>
          </div>

          <div className="pb-4 text-center">
            <span className="text-sm" style={{ color: '#62C8DF' }}>Share Marrow</span>
          </div>
        </div>
      </div>
    </>
  );
}
