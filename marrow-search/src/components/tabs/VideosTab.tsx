import TabHeader from '../layout/TabHeader';
import {
  Download, Play, ChevronRight, ChevronDown,
  Bone, Dna, Heart, Pill, Microscope, FlaskConical,
  Users, Stethoscope, Scissors, Baby, Ear, Eye,
  Scale, Brain, PersonStanding, Syringe,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type Props = { onSearchOpen: () => void };

type Subject = { name: string; done: number; total: number; Icon: LucideIcon };

const subjects: Subject[] = [
  { name: 'Anatomy', done: 1, total: 84, Icon: Bone },
  { name: 'Biochemistry', done: 1, total: 53, Icon: Dna },
  { name: 'Physiology', done: 0, total: 62, Icon: Heart },
  { name: 'Pharmacology', done: 4, total: 75, Icon: Pill },
  { name: 'Pathology', done: 2, total: 68, Icon: FlaskConical },
  { name: 'Microbiology', done: 0, total: 42, Icon: Microscope },
  { name: 'Community Medicine', done: 3, total: 55, Icon: Users },
  { name: 'Medicine', done: 5, total: 95, Icon: Stethoscope },
  { name: 'Surgery', done: 2, total: 80, Icon: Scissors },
  { name: 'Obstetrics & Gynecology', done: 1, total: 65, Icon: Baby },
  { name: 'Pediatrics', done: 0, total: 50, Icon: Baby },
  { name: 'ENT', done: 0, total: 32, Icon: Ear },
  { name: 'Ophthalmology', done: 0, total: 28, Icon: Eye },
  { name: 'Forensic Medicine', done: 0, total: 25, Icon: Scale },
  { name: 'Psychiatry', done: 0, total: 22, Icon: Brain },
  { name: 'Orthopedics', done: 1, total: 38, Icon: PersonStanding },
  { name: 'Dermatology', done: 0, total: 28, Icon: Pill },
  { name: 'Radiology', done: 0, total: 18, Icon: FlaskConical },
  { name: 'Anesthesia', done: 0, total: 15, Icon: Syringe },
];

export default function VideosTab({ onSearchOpen }: Props) {
  return (
    <>
      <TabHeader title="Videos Edition 8" onSearchOpen={onSearchOpen} />
      <div className="flex-1 overflow-y-auto" style={{ background: '#F7F7F5' }}>
        <div className="p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <button
              className="rounded-xl bg-white py-2.5 flex items-center justify-center gap-2"
              style={{ border: '1px solid rgba(0,0,0,0.08)', cursor: 'pointer' }}
            >
              <Download size={16} className="text-gray-500" />
              <span className="text-sm text-gray-600">Downloaded</span>
            </button>
            <button
              className="rounded-xl bg-white py-2.5 flex items-center justify-center gap-2"
              style={{ border: '1px solid rgba(0,0,0,0.08)', cursor: 'pointer' }}
            >
              <Play size={16} style={{ color: '#62C8DF' }} />
              <span className="text-sm text-gray-600">Sample Videos</span>
            </button>
          </div>

          <div
            className="rounded-xl p-4 flex items-center justify-between"
            style={{ background: '#FAEEDA', border: '1px solid rgba(0,0,0,0.08)' }}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center"
                style={{ background: '#F9A825' }}
              >
                🔄
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <p className="text-sm font-medium text-gray-700">World of Revision</p>
                  <span
                    className="text-xs px-1.5 py-0.5 rounded font-medium text-white"
                    style={{ background: '#0F6E56' }}
                  >
                    NEW
                  </span>
                </div>
                <p className="text-xs text-gray-500">+ MCQ discussions Videos</p>
              </div>
            </div>
            <ChevronRight size={16} className="text-gray-400" />
          </div>

          <div>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Watch Next</p>
            <div className="rounded-xl bg-white p-3 flex items-center gap-3" style={{ border: '1px solid rgba(0,0,0,0.08)' }}>
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ background: '#E6F1FB' }}
              >
                <Play size={16} style={{ color: '#378ADD' }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: '#378ADD' }}>
                  Pharmacokinetics: Metabolism
                </p>
                <p className="text-xs text-gray-400">38 Min video</p>
              </div>
              <ChevronRight size={16} className="text-gray-300" />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Subjects</p>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400">Sort by: Default</span>
              <ChevronDown size={12} className="text-gray-400" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {subjects.map((s) => (
              <div
                key={s.name}
                className="rounded-xl bg-white p-3 flex flex-col items-center"
                style={{ border: '1px solid rgba(0,0,0,0.08)' }}
              >
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center mb-2"
                  style={{ background: '#E6F1FB' }}
                >
                  <s.Icon size={28} style={{ color: '#378ADD' }} />
                </div>
                <p className="text-sm font-medium text-gray-700 text-center leading-tight">{s.name}</p>
                <p className="text-xs text-gray-400 mt-0.5">{s.done}/{s.total} modules</p>
                <div className="w-full h-1 rounded-full mt-1.5" style={{ background: '#e5e7eb' }}>
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${s.done > 0 ? Math.max((s.done / s.total) * 100, 4) : 0}%`,
                      background: '#9CCC65',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
