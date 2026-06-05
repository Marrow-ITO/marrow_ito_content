import type { SearchResponse, SearchResult, SuggestResponse, Suggestion } from '../types';

// ─── helpers ──────────────────────────────────────────────────────────────────

function v(id: string, title: string, subject: string, meta: string, matchType: 'exact' | 'related', concept: string, best?: true): SearchResult {
  return { id, type: 'video', title, subject, metadata: meta, match_type: matchType, match_concept: concept, is_best_match: best, start_time: 0 };
}
function ts(id: string, title: string, subject: string, meta: string, startTime: number, matchType: 'exact' | 'related', concept: string): SearchResult {
  return { id, type: 'timestamp', title, subject, metadata: meta, match_type: matchType, match_concept: concept, start_time: startTime };
}
function q(id: string, title: string, subject: string, meta: string, matchType: 'exact' | 'related', concept: string, best?: true): SearchResult {
  return { id, type: 'qbank', title, subject, metadata: meta, match_type: matchType, match_concept: concept, is_best_match: best };
}
function p(id: string, title: string, subject: string, meta: string, concept: string): SearchResult {
  return { id, type: 'pearl', title, subject, metadata: meta, match_type: 'exact', match_concept: concept };
}
function m(id: string, title: string, subject: string, meta: string, matchType: 'exact' | 'related', concept: string): SearchResult {
  return { id, type: 'module', title, subject, metadata: meta, match_type: matchType, match_concept: concept };
}
function n(id: string, contentId: string, title: string, subject: string, meta: string, pageNo: number, snippet: string, concept: string): SearchResult {
  return { id, content_id: contentId, type: 'note', title, subject, metadata: meta, page_no: pageNo, snippet, match_type: 'exact', match_concept: concept };
}
function ru(id: string, contentId: string, title: string, subject: string, meta: string, dateOfUpdate: string, snippet: string, referenceLink: string, concept: string): SearchResult {
  return { id, content_id: contentId, recent_update_id: contentId, type: 'recent_update', title, subject, metadata: meta, date_of_update: dateOfUpdate, snippet, reference_link: referenceLink, match_type: 'exact', match_concept: concept };
}

// ─── autosuggest data ─────────────────────────────────────────────────────────

const SUGGESTIONS: Record<string, Suggestion[]> = {
  heart: [
    { text: 'Heart Failure', context: 'Cardiovascular · most searched', type: 'concept' },
    { text: 'Heart Failure — drugs', context: '↳ Carvedilol, Spironolactone', type: 'subtopic' },
    { text: 'Heart Failure — classification', context: '↳ HFrEF vs HFpEF', type: 'subtopic' },
    { text: 'Heart sounds', context: '↳ auscultation guide', type: 'subtopic' },
  ],
  ibd: [
    { text: 'IBD', context: 'Inflammatory Bowel Disease', type: 'concept' },
    { text: 'Ulcerative Colitis', context: '↳ a type of IBD', type: 'disambiguation' },
    { text: "Crohn's Disease", context: '↳ a type of IBD', type: 'disambiguation' },
    { text: 'IBD — management', context: '↳ common next step', type: 'intent' },
    { text: 'IBD vs IBS', context: '↳ frequently confused', type: 'disambiguation' },
  ],
  mi: [
    { text: 'MI', context: 'Myocardial Infarction', type: 'concept' },
    { text: 'MI — STEMI management', context: '↳ emergency protocol', type: 'intent' },
    { text: 'MI — biomarkers', context: '↳ Troponin, CK-MB', type: 'subtopic' },
    { text: 'MI vs angina', context: '↳ frequently confused', type: 'disambiguation' },
  ],
  beta: [
    { text: 'beta blockers', context: 'Pharmacology · mechanism', type: 'concept' },
    { text: 'beta blockers in heart failure', context: '↳ Carvedilol, Metoprolol', type: 'subtopic' },
    { text: 'beta blockers — side effects', context: '↳ contraindications & cautions', type: 'subtopic' },
    { text: 'beta blockers vs CCBs', context: '↳ comparison', type: 'disambiguation' },
  ],
  mech: [
    { text: 'mechanism of beta blockers', context: 'Pharmacology · common intent', type: 'intent' },
    { text: 'mechanism of ACE inhibitors', context: '↳ RAAS pathway', type: 'subtopic' },
    { text: 'mechanism of statins', context: '↳ HMG-CoA reductase', type: 'subtopic' },
  ],
  pant: [
    { text: 'Pantoprazole', context: 'Pharmacology · PPI drug', type: 'concept' },
    { text: 'Pantoprazole — mechanism', context: '↳ proton pump inhibition', type: 'subtopic' },
    { text: 'PPIs — comparison', context: '↳ Omeprazole vs Pantoprazole', type: 'disambiguation' },
  ],
  bowl: [
    { text: 'Bowel obstruction', context: 'Surgery · emergency', type: 'concept' },
    { text: 'Inflammatory Bowel Disease', context: "↳ IBD — UC + Crohn's", type: 'concept' },
    { text: 'Bowel sounds', context: '↳ auscultation significance', type: 'subtopic' },
  ],
  generic: [
    { text: 'Cardiac cycle', context: 'Physiology · high yield', type: 'concept' },
    { text: 'Anti-TB drugs', context: '↳ Pharmacology', type: 'subtopic' },
    { text: 'Renal physiology', context: '↳ GFR, tubular function', type: 'subtopic' },
    { text: 'Acid–base disorders', context: '↳ metabolic vs respiratory', type: 'subtopic' },
  ],
};

function getSuggestionKey(q: string): string {
  const ql = q.toLowerCase().trim();
  if (ql.startsWith('heart')) return 'heart';
  if (ql === 'ibd' || ql.startsWith('ibd')) return 'ibd';
  if (ql === 'mi' || ql.startsWith('mi ') || ql.startsWith('myo')) return 'mi';
  if (ql.startsWith('beta')) return 'beta';
  if (ql.startsWith('mec') || ql.startsWith('mechanism')) return 'mech';
  if (ql.startsWith('pant')) return 'pant';
  if (ql.startsWith('bowl') || ql.startsWith('bow')) return 'bowl';
  return 'generic';
}

// ─── search responses ─────────────────────────────────────────────────────────

const RESPONSES: Record<string, SearchResponse> = {

  // ── heart failure: 6 videos, 4 qbank, 2 pearls ───────────────────────────
  'heart failure': {
    query: 'heart failure',
    interpreted_as: 'Heart Failure',
    related_concepts: ['HFrEF', 'HFpEF', 'Cardiomyopathy'],
    results: [
      v('hf-v1', 'Heart Failure — Pathophysiology & Types', 'Medicine', '52 Min · ★ 4.8', 'exact', 'Heart Failure', true),
      v('hf-v2', 'Heart Failure — Management & Drugs', 'Medicine', '44 Min · ★ 4.7', 'exact', 'Heart Failure'),
      v('hf-v3', 'Acute Decompensated Heart Failure — Emergency', 'Medicine', '36 Min · ★ 4.6', 'related', 'HFrEF'),
      v('hf-v4', 'Diuretics in Heart Failure — Pharmacology', 'Pharmacology', '28 Min · ★ 4.7', 'related', 'HFpEF'),
      v('hf-v5', 'Cardiac Remodelling — Pathophysiology', 'Physiology', '42 Min · ★ 4.5', 'related', 'Cardiomyopathy'),
      v('hf-v6', 'NYHA Classification & Staging of HF', 'Medicine', '22 Min · ★ 4.6', 'exact', 'Heart Failure'),
      q('hf-q1', 'Heart Failure — High-yield MCQs', 'Medicine', '38 questions', 'exact', 'Heart Failure'),
      q('hf-q2', 'Cardiomyopathy & HF — MCQs', 'Medicine', '24 questions', 'related', 'Cardiomyopathy'),
      q('hf-q3', 'HFrEF vs HFpEF — MCQ set', 'Medicine', '18 questions', 'related', 'HFrEF'),
      q('hf-q4', 'Cardiac Failure — Grand Round MCQs', 'Medicine', '30 questions', 'related', 'HFpEF'),
      p('hf-p1', 'Heart Failure — Key pearls & mnemonics', 'Medicine', '12 pearls', 'Heart Failure'),
      p('hf-p2', 'Cardiac Remodelling — High-yield pearls', 'Medicine', '8 pearls', 'Cardiomyopathy'),
      n('hf-n1', '6a217ca74e72759ee47c4fee', 'Heart Failure — Pathophysiology', 'The Cardiovascular System', 'Page 3 · Cardiology', 3, 'Frank-Starling mechanism compensates in early HF by increasing stroke volume. As the disease progresses, ventricular remodelling leads to increased wall stress and further decline in ejection fraction...', 'Heart Failure'),
      n('hf-n2', '6a217ca74e72759ee47c4fef', 'Heart Failure — Drug Therapy Notes', 'Pharmacology', 'Page 7 · Pharmacology', 7, 'ACE inhibitors reduce afterload and prevent adverse remodelling. Beta-blockers reduce heart rate and improve ejection fraction over time. Loop diuretics relieve congestion symptoms...', 'Heart Failure'),
      ru('ru_hf_001', '6a2217ac0520a40beb869010', 'ESC Heart Failure Guidelines 2023 — Key Updates to Device Therapy & SGLT2 Inhibitors', 'Medicine', 'Recent update · 2023-08-15 · Medicine · European Society of Cardiology', '2023-08-15', 'SGLT2 inhibitors (dapagliflozin, empagliflozin) are now Class I recommendations for HFrEF regardless of diabetes status. CRT indications expanded. Vericiguat added as second-line for worsening HF.', 'https://academic.oup.com/eurheartj/article/44/36/3505/7246292', 'Heart Failure'),
    ],
  },

  // ── IBD: 7 videos (incl. 1 timestamp), 4 qbank, 2 modules ────────────────
  'ibd': {
    query: 'IBD',
    interpreted_as: 'Inflammatory Bowel Disease',
    related_concepts: ['Ulcerative Colitis', "Crohn's Disease"],
    results: [
      v('ibd-v1', 'Inflammatory Bowel Disease — Overview', 'Medicine', '42 Min · ★ 4.7', 'exact', 'IBD', true),
      ts('ibd-v2', 'Ulcerative Colitis segment', "in 'IBD' lecture", '@ 12:30', 750, 'related', 'Ulcerative Colitis'),
      v('ibd-v3', "Crohn's Disease — Surgical management", 'Surgery', '28 Min · ★ 4.5', 'related', "Crohn's Disease"),
      v('ibd-v4', 'UC — Medical Management & Biologics', 'Medicine', '38 Min · ★ 4.6', 'related', 'Ulcerative Colitis'),
      v('ibd-v5', "Crohn's Disease — Pathology & Imaging", 'Pathology', '30 Min · ★ 4.5', 'related', "Crohn's Disease"),
      v('ibd-v6', 'IBD — Extraintestinal Manifestations', 'Medicine', '24 Min · ★ 4.7', 'related', 'IBD'),
      v('ibd-v7', 'IBD vs IBS — Key Differences', 'Medicine', '20 Min · ★ 4.4', 'related', 'IBD vs IBS'),
      q('ibd-q1', 'IBD — High-yield MCQs', 'Medicine', '34 questions', 'exact', 'IBD'),
      q('ibd-q2', "Ulcerative Colitis vs Crohn's", 'Pathology', '18 questions', 'related', 'UC / Crohn\'s'),
      q('ibd-q3', "Crohn's — Surgical Complications MCQs", 'Surgery', '22 questions', 'related', "Crohn's Disease"),
      q('ibd-q4', 'UC Drug Therapy — MCQ set', 'Medicine', '20 questions', 'related', 'Ulcerative Colitis'),
      m('ibd-m1', 'IBD — Complete Review Module', 'Medicine', '45 topics', 'exact', 'IBD'),
      m('ibd-m2', "Crohn's Disease — Complete Module", 'Surgery', '30 topics', 'related', "Crohn's Disease"),
      n('ibd-n1', '6a217ca74e72759ee47c4ff0', 'Inflammatory Bowel Disease — Overview Notes', 'Gastroenterology', 'Page 2 · Medicine', 2, "UC involves continuous mucosal inflammation from rectum proximally. Crohn's disease can affect any part of GI tract with skip lesions. Both present with bloody diarrhea, abdominal pain, and weight loss...", 'IBD'),
      n('ibd-n2', '6a217ca74e72759ee47c4ff1', 'IBD — Extraintestinal Manifestations', 'Gastroenterology', 'Page 5 · Medicine', 5, 'Joint involvement (arthritis), eye involvement (uveitis, episcleritis), skin manifestations (pyoderma gangrenosum, erythema nodosum), liver disease (PSC in UC)...', 'Inflammatory Bowel Disease'),
      ru('ru_ibd_001', '6a2217ac0520a40beb869028', 'ACG Clinical Guideline: Ulcerative Colitis — Updated Management Algorithm 2025', 'Medicine', 'Recent update · 2025-09-10 · Medicine · American College of Gastroenterology', '2025-09-10', 'ACG updated its UC management guidelines recommending earlier escalation to biologics in moderate-to-severe disease. Vedolizumab and ustekinumab are now positioned alongside TNF inhibitors as first-line advanced therapy...', 'https://journals.lww.com/ajg/acg-uc-guideline', 'IBD'),
    ],
  },

  // ── MI: 6 videos (incl. 1 timestamp), 5 qbank, 3 pearls ─────────────────
  'mi': {
    query: 'MI',
    interpreted_as: 'Myocardial Infarction',
    related_concepts: ['ACS', 'STEMI', 'Cardiac enzymes'],
    results: [
      v('mi-v1', 'Myocardial Infarction — Overview & Pathophysiology', 'Medicine', '48 Min · ★ 4.9', 'exact', 'MI', true),
      v('mi-v2', 'STEMI — ECG & Emergency Management', 'Medicine', '36 Min · ★ 4.8', 'related', 'STEMI'),
      ts('mi-v3', 'Cardiac biomarkers — Troponin & CK-MB', "in 'ACS' lecture", '@ 18:45', 1125, 'related', 'Cardiac enzymes'),
      v('mi-v4', 'ACS — Clinical Presentation & Diagnosis', 'Medicine', '42 Min · ★ 4.8', 'related', 'ACS'),
      v('mi-v5', 'NSTEMI — Management Protocol', 'Medicine', '34 Min · ★ 4.7', 'related', 'ACS'),
      v('mi-v6', 'Post-MI Complications & Prognosis', 'Medicine', '28 Min · ★ 4.6', 'related', 'STEMI'),
      q('mi-q1', 'MI & ACS — High-yield MCQs', 'Medicine', '45 questions', 'exact', 'MI'),
      q('mi-q2', 'Cardiac enzymes — MCQ set', 'Biochemistry', '22 questions', 'related', 'Cardiac enzymes'),
      q('mi-q3', 'ACS — Emergency Management MCQs', 'Medicine', '35 questions', 'related', 'ACS'),
      q('mi-q4', 'MI — ECG Changes & Interpretation', 'Medicine', '28 questions', 'related', 'STEMI'),
      q('mi-q5', 'Cardiac Biomarkers — High-yield MCQs', 'Biochemistry', '20 questions', 'related', 'Cardiac enzymes'),
      p('mi-p1', 'MI — Key clinical pearls', 'Medicine', '15 pearls', 'MI'),
      p('mi-p2', 'STEMI vs NSTEMI — Quick pearls', 'Medicine', '10 pearls', 'STEMI'),
      p('mi-p3', 'Cardiac enzymes — Timing pearls', 'Medicine', '8 pearls', 'Cardiac enzymes'),
    ],
  },

  // ── mechanism of beta blockers in HF: 5 videos, 3 qbank, 2 modules ───────
  'mechanism of beta blockers in hf': {
    query: 'mechanism of beta blockers in HF',
    interpreted_as: 'Beta-blockers in Heart Failure — mechanism',
    related_concepts: ['Carvedilol', 'Metoprolol', 'SNS blockade'],
    results: [
      v('bb-v1', 'Beta-blockers — Mechanism & Pharmacology', 'Pharmacology', '34 Min · ★ 4.8', 'exact', 'Beta-blockers', true),
      ts('bb-v2', 'Carvedilol in HF — Clinical use', "in 'Heart Failure drugs' lecture", '@ 22:10', 1330, 'related', 'Carvedilol'),
      v('bb-v3', 'SNS blockade & Cardiac remodelling', 'Physiology', '28 Min · ★ 4.6', 'related', 'SNS blockade'),
      v('bb-v4', 'ACE Inhibitors & RAAS in Heart Failure', 'Pharmacology', '28 Min · ★ 4.7', 'related', 'SNS blockade'),
      v('bb-v5', 'Beta-blocker Comparison — Cardioselectivity', 'Pharmacology', '32 Min · ★ 4.6', 'exact', 'Beta-blockers'),
      q('bb-q1', 'Beta-blockers in Cardiology — MCQs', 'Pharmacology', '30 questions', 'exact', 'Beta-blockers'),
      q('bb-q2', 'Heart Failure drugs — Mechanism MCQs', 'Medicine', '25 questions', 'related', 'HF Pharmacotherapy'),
      q('bb-q3', 'Beta-blockers — Clinical Pharmacology MCQs', 'Pharmacology', '22 questions', 'related', 'Metoprolol'),
      m('bb-m1', 'Beta-blockers — Complete Pharmacology Module', 'Pharmacology', '25 topics', 'exact', 'Beta-blockers'),
      m('bb-m2', 'HF Management — Evidence-based Module', 'Medicine', '35 topics', 'related', 'HF Pharmacotherapy'),
    ],
  },

  // ── pantaprazole: 4 videos (incl. 1 timestamp), 3 qbank ──────────────────
  'pantaprazole': {
    query: 'pantaprazole',
    interpreted_as: 'Pantoprazole',
    related_concepts: ['PPIs', 'Proton pump inhibitor', 'GERD'],
    results: [
      v('ppi-v1', 'Proton Pump Inhibitors — Mechanism & Uses', 'Pharmacology', '30 Min · ★ 4.7', 'exact', 'Pantoprazole', true),
      ts('ppi-v2', 'Pantoprazole — drug profile', "in 'GI Pharmacology' lecture", '@ 8:15', 495, 'exact', 'Pantoprazole'),
      v('ppi-v3', 'GERD — Pathophysiology & Management', 'Medicine', '36 Min · ★ 4.6', 'related', 'GERD'),
      v('ppi-v4', 'H. pylori — Diagnosis & PPI Therapy', 'Microbiology', '28 Min · ★ 4.5', 'related', 'PPIs'),
      q('ppi-q1', 'PPIs & Anti-ulcer drugs — MCQs', 'Pharmacology', '28 questions', 'exact', 'Pantoprazole'),
      q('ppi-q2', 'Acid Peptic Disorders — MCQs', 'Medicine', '32 questions', 'related', 'PPIs'),
      q('ppi-q3', 'H. pylori Treatment — MCQ set', 'Microbiology', '18 questions', 'related', 'GERD'),
    ],
  },

  // ── bowl inflamation: no results ──────────────────────────────────────────
  'bowl inflamation': {
    query: 'bowl inflamation',
    interpreted_as: null,
    related_concepts: [],
    no_results: true,
    suggestions: ['Inflammatory Bowel Disease', 'Ulcerative Colitis', 'Bowel obstruction'],
    results: [],
  },
};

// Generic fallback — no results for any unrecognised query
function fallbackResponse(query: string): SearchResponse {
  return {
    query,
    interpreted_as: null,
    related_concepts: [],
    no_results: true,
    suggestions: [],
    results: [],
  };
}

// ─── public API ───────────────────────────────────────────────────────────────

export function search(rawQuery: string): Promise<SearchResponse> {
  const key = rawQuery.trim().toLowerCase();
  const response = RESPONSES[key] ?? fallbackResponse(rawQuery.trim());
  return Promise.resolve(response);
}

export function getSuggestions(query: string): Promise<SuggestResponse> {
  const key = getSuggestionKey(query);
  return Promise.resolve({
    query,
    suggestions: SUGGESTIONS[key] ?? SUGGESTIONS.generic,
  });
}
