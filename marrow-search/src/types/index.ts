export type TabId = 'home' | 'qbank' | 'tests' | 'videos';

export type VideoChapter = {
  title: string;
  timestamp: string;
};

export type RelatedModule = {
  id: string;
  title: string;
  subject: string;
  rating: number;
  mcqCount: number;
  progressPercent: number;
  completedDate?: string;
  thumbnailColor: string;
};

export type VideoPageData = {
  id: string;
  title: string;
  subject: string;
  youtubeVideoId: string;
  startAtSeconds?: number;
  chapters: VideoChapter[];
  relatedModules: RelatedModule[];
};

export type NoteImage = {
  id: string;
  image_data: string;
  mime_type: string;
  order: number;
};

export type SearchResponse = {
  query: string;
  interpreted_as: string | null;
  related_concepts: string[];
  results: SearchResult[];
  no_results?: boolean;
  suggestions?: string[];
};

export type SearchResult = {
  id: string;
  content_id?: string;
  type: 'video' | 'timestamp' | 'qbank' | 'module' | 'pearl' | 'clinical_q' | 'note' | 'recent_update';
  title: string;
  subject: string;
  metadata: string;
  match_type: 'exact' | 'related';
  match_concept: string;
  is_best_match?: boolean;
  thumbnail?: string;
  thumbnail_url?: string;
  start_time?: number;
  snippet?: string;
  page_no?: number;
  video_content_id?: string;
  date_of_update?: string;
  reference_link?: string;
  recent_update_id?: string;
};

export type VideoApiResponse = {
  id: string;
  video_id: string;
  title: string;
  subject_name: string;
  topic_name: string;
  lesson_name: string;
  lesson_id: string;
  subject_id: string;
  topic_id: string;
  url: string;
  file_name: string;
  description: string | null;
  duration_seconds: number | null;
  notes: NoteImage[];
};

export type SuggestResponse = {
  query: string;
  suggestions: Suggestion[];
};

export type Suggestion = {
  text: string;
  context?: string;
  type: 'concept' | 'subtopic' | 'intent' | 'disambiguation';
};
