import { search as mockSearch, getSuggestions as mockGetSuggestions } from './mockApi';
import type { SearchResponse, SuggestResponse, VideoApiResponse } from '../types';

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API !== 'false';
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = {
  async search(query: string): Promise<SearchResponse> {
    if (USE_MOCK) return mockSearch(query);
    const res = await fetch(`${BASE_URL}/api/search?q=${encodeURIComponent(query)}`);
    return res.json() as Promise<SearchResponse>;
  },

  async getSuggestions(query: string): Promise<SuggestResponse> {
    if (USE_MOCK) return mockGetSuggestions(query);
    const res = await fetch(`${BASE_URL}/api/suggest?q=${encodeURIComponent(query)}`);
    return res.json() as Promise<SuggestResponse>;
  },
};

export async function fetchVideoDetail(contentId: string): Promise<VideoApiResponse> {
  const base = import.meta.env.VITE_API_BASE_URL ?? 'http://3.6.39.50:5001';
  const res = await fetch(`${base}/api/videos/${contentId}`);
  if (!res.ok) throw new Error(`Video API error: ${res.status}`);
  return res.json();
}
