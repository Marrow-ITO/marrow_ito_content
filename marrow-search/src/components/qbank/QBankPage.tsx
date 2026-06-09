import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Bookmark } from 'lucide-react';
import { fetchQBankDetail } from '../../lib/apiClient';
import type { SearchResult, QBankApiResponse } from '../../types';

type QBankPageProps = {
  result: SearchResult;
  onBack: () => void;
};

export default function QBankPage({ result, onBack }: QBankPageProps) {
  const [qbankApi, setQbankApi] = useState<QBankApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchQBankDetail(result.content_id ?? result.id)
      .then(setQbankApi)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [result.content_id, result.id]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Teal header */}
      <div className="bg-[#62C8DF] px-4 py-3 flex items-center gap-3 flex-shrink-0">
        <button onClick={onBack}>
          <ChevronLeft size={22} className="text-white" />
        </button>
        <h1 className="text-white font-medium text-base truncate">
          {qbankApi?.title ?? '...'}
        </h1>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto bg-[#F7F7F5]">
        {loading && (
          <div className="animate-pulse space-y-3 p-4">
            <div className="h-6 bg-gray-200 rounded w-1/3" />
            <div className="h-8 bg-gray-200 rounded w-3/4" />
            <div className="h-20 bg-gray-200 rounded-xl" />
            <div className="h-10 bg-gray-200 rounded-xl" />
          </div>
        )}

        {error && !loading && (
          <div className="flex items-center justify-center h-40">
            <p className="text-sm text-gray-500 text-center px-6">
              Could not load questions. Please try again.
            </p>
          </div>
        )}

        {qbankApi && !loading && (
          <>
            {/* Section 1 — Subject + Title */}
            <div className="px-4 pt-5 pb-4 bg-white">
              <p className="text-sm font-medium text-[#62C8DF] mb-1">
                {qbankApi.subject_name}
              </p>
              <h2 className="text-xl font-bold text-gray-800 leading-snug">
                {qbankApi.title}
              </h2>
            </div>
            <div className="h-px bg-gray-200 mx-4" />

            {/* Section 2 — MCQ count card with SOLVE button */}
            <div className="mx-4 mt-4">
              <div className="bg-white rounded-xl border border-black/10 px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-lg font-bold text-gray-700">
                    {qbankApi.mcq_count} MCQs
                  </p>
                  <p className="text-sm text-gray-400">Solve now</p>
                </div>
                <button className="bg-[#62C8DF] text-white text-sm font-bold uppercase tracking-wider px-5 py-2 rounded-lg">
                  SOLVE
                </button>
              </div>
            </div>

            {/* Section 3 — Bookmarks row */}
            <div className="mx-4 mt-3 flex items-center gap-2 text-sm text-gray-600 py-2">
              <Bookmark size={16} className="text-[#62C8DF] fill-[#62C8DF]" />
              <span>0 Bookmarks</span>
              <ChevronRight size={16} className="text-gray-400 ml-auto" />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
