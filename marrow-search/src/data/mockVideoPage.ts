import type { VideoPageData } from '../types';

export const mockVideoPage: VideoPageData = {
  id: 'vid_pharmacokinetics_metabolism',
  title: 'Pharmacokinetics: Metabolism',
  subject: 'Pharmacology',
  youtubeVideoId: 'PBZZ_Cu64aQ',
  startAtSeconds: 600,
  chapters: [
    { title: 'Introduction & Overview',        timestamp: '00:00:00' },
    { title: 'Phase I Reactions — Oxidation',  timestamp: '00:04:32' },
    { title: 'Phase II Reactions — Conjugation', timestamp: '00:12:18' },
    { title: 'First Pass Effect',              timestamp: '00:21:45' },
    { title: 'Drug Interactions via CYP450',   timestamp: '00:31:10' },
  ],
  relatedModules: [
    {
      id: 'mod_pharmacokinetics_absorption',
      title: 'Pharmacokinetics: Absorption & Distribution',
      subject: 'Pharmacology',
      rating: 4.7,
      mcqCount: 22,
      progressPercent: 100,
      completedDate: '28 May 2026',
      thumbnailColor: '#E3F2FD',
    },
    {
      id: 'mod_pharmacokinetics_excretion',
      title: 'Pharmacokinetics: Excretion & Bioavailability',
      subject: 'Pharmacology',
      rating: 4.5,
      mcqCount: 18,
      progressPercent: 45,
      thumbnailColor: '#E8F5E9',
    },
  ],
};
