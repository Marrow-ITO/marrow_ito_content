import TabHeader from '../layout/TabHeader';
import {
  TrendingUp, ChevronRight, Bookmark, Plus,
  Bone, Dna, Heart, Pill, Microscope, FlaskConical,
  Users, Stethoscope, Scissors, Baby, Ear, Eye,
  Scale, Brain, PersonStanding, Syringe,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type Props = { onSearchOpen: () => void };

type Subject = { name: string; done: number; total: number; Icon: LucideIcon };

const subjects: Subject[] = [
  { name: 'Anatomy', done: 63, total: 63, Icon: Bone },
  { name: 'Biochemistry', done: 28, total: 28, Icon: Dna },
  { name: 'Physiology', done: 43, total: 43, Icon: Heart },
  { name: 'Pharmacology', done: 67, total: 67, Icon: Pill },
  { name: 'Microbiology', done: 35, total: 35, Icon: Microscope },
  { name: 'Pathology', done: 70, total: 71, Icon: FlaskConical },
  { name: 'Community Medicine', done: 45, total: 45, Icon: Users },
  { name: 'Medicine', done: 89, total: 92, Icon: Stethoscope },
  { name: 'Surgery', done: 72, total: 75, Icon: Scissors },
  { name: 'Obstetrics & Gynecology', done: 58, total: 60, Icon: Baby },
  { name: 'Pediatrics', done: 42, total: 44, Icon: Baby },
  { name: 'ENT', done: 28, total: 30, Icon: Ear },
  { name: 'Ophthalmology', done: 25, total: 26, Icon: Eye },
  { name: 'Forensic Medicine', done: 22, total: 23, Icon: Scale },
  { name: 'Psychiatry', done: 18, total: 20, Icon: Brain },
  { name: 'Orthopedics', done: 31, total: 35, Icon: PersonStanding },
  { name: 'Dermatology', done: 24, total: 25, Icon: Pill },
  { name: 'Radiology', done: 15, total: 18, Icon: FlaskConical },
  { name: 'Anesthesia', done: 12, total: 14, Icon: Syringe },
];

export default function QBankTab({ onSearchOpen }: Props) {
  return (
    <>
      <TabHeader title="QBank Edition 8" onSearchOpen={onSearchOpen} />
      <div className="flex-1 overflow-y-auto" style={{ background: '#F7F7F5' }}>
        <div className="p-4 space-y-3">
          <div
            className="rounded-xl bg-white p-3 flex items-center justify-between"
            style={{ border: '1px solid rgba(0,0,0,0.08)' }}
          >
            <div className="flex items-center gap-2">
              <TrendingUp size={18} style={{ color: '#62C8DF' }} />
              <span className="text-sm text-gray-700">QBank tracker</span>
            </div>
            <ChevronRight size={16} className="text-gray-300" />
          </div>

          <div
            className="rounded-xl bg-white px-3 py-2.5 flex items-center gap-2"
            style={{ border: '1px solid rgba(0,0,0,0.08)' }}
          >
            <span className="text-xs text-gray-400">Solve Next</span>
            <span className="text-sm font-medium truncate flex-1" style={{ color: '#62C8DF' }}>
              National Health Programmes II – NLEP, N…
            </span>
            <ChevronRight size={16} className="text-gray-300" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div
              className="rounded-xl bg-white p-3 flex items-center gap-2"
              style={{ border: '1px solid rgba(0,0,0,0.08)' }}
            >
              <Bookmark size={18} style={{ color: '#378ADD' }} />
              <div>
                <p className="text-sm font-medium text-gray-700">Bookmarks</p>
                <p className="text-xs text-gray-400">36 bookmarks</p>
              </div>
            </div>
            <div
              className="rounded-xl bg-white p-3 flex items-center gap-2"
              style={{ border: '1px solid rgba(0,0,0,0.08)' }}
            >
              <Plus size={18} style={{ color: '#62C8DF' }} />
              <div>
                <p className="text-sm font-medium text-gray-700">Custom Module</p>
                <p className="text-xs text-gray-400">Customised MCQs</p>
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-white overflow-hidden" style={{ border: '1px solid rgba(0,0,0,0.08)' }}>
            {subjects.map((s, i) => (
              <div
                key={s.name}
                className="px-4 py-3"
                style={{ borderTop: i > 0 ? '1px solid rgba(0,0,0,0.06)' : undefined }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: '#E6F1FB' }}
                  >
                    <s.Icon size={16} style={{ color: '#378ADD' }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-700">{s.name}</p>
                    <div className="h-1.5 rounded-full mt-1.5 overflow-hidden" style={{ background: '#e5e7eb' }}>
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${(s.done / s.total) * 100}%`, background: '#9CCC65' }}
                      />
                    </div>
                    <p className="text-xs mt-0.5" style={{ color: s.done === s.total ? '#9CCC65' : '#9ca3af' }}>
                      {s.done === s.total ? '✓ ' : ''}{s.done}/{s.total} modules
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
