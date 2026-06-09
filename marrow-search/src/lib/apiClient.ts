import { search as mockSearch, getSuggestions as mockGetSuggestions } from './mockApi';
import type { SearchResponse, SuggestResponse, VideoApiResponse, QBankApiResponse } from '../types';

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API !== 'false';
const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'https://marrow-ito.dailyrounds.org:8443'
).replace(/\/$/, '');

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
  const res = await fetch(`${BASE_URL}/api/videos/${contentId}`);
  if (!res.ok) throw new Error(`Video API error: ${res.status}`);
  return res.json();
}

export async function fetchQBankDetail(contentId: string): Promise<QBankApiResponse> {
  const res = await fetch(`${BASE_URL}/api/qbank/${contentId}`);
  if (!res.ok) throw new Error(`QBank API error: ${res.status}`);
  return res.json();
}
