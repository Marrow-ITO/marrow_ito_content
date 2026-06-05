import { useState, useEffect } from 'react';
import {
  ChevronLeft, Download, BookOpen, PlayCircle, CheckCircle2, Star,
} from 'lucide-react';
import NotesSheet from './NotesSheet';
import { fetchVideoDetail } from '../../lib/apiClient';
import { mockVideoPage } from '../../data/mockVideoPage';
import type { SearchResult, VideoApiResponse } from '../../types';

type Props = {
  result: SearchResult;
  onBack: () => void;
  autoOpenNotes?: boolean;
  initialNotesPage?: number;
};

// Skeleton block helper
function Skeleton({ width, height }: { width: string; height: number }) {
  return (
    <div
      style={{
        width, height, borderRadius: 6,
        background: '#e5e7eb',
        animation: 'pulse 1.5s ease-in-out infinite',
      }}
    />
  );
}

export default function VideoPage({ result, onBack, autoOpenNotes, initialNotesPage }: Props) {
  const [videoApi, setVideoApi] = useState<VideoApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [notesOpen, setNotesOpen] = useState(autoOpenNotes ?? false);

  const contentId = result.type === 'note'
    ? (result.video_content_id ?? result.content_id)
    : result.content_id;

  function load() {
    setLoading(true);
    setError(false);
    fetchVideoDetail(contentId ?? '')
      .then(setVideoApi)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [contentId]);

  const startAt = result.start_time ?? 0;
  const shouldAutoplay = result.type === 'video' || result.type === 'timestamp';

  const notesImages = [...(videoApi?.notes ?? [])]
    .sort((a, b) => a.order - b.order)
    .map(n => `data:${n.mime_type};base64,${n.image_data}`);
  const notesPageCount = notesImages.length;

  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column', flex: 1,
        overflow: 'hidden', background: 'white', position: 'relative',
      }}
    >
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }`}</style>

      {/* ── Video area ── */}
      <div style={{ position: 'relative', flexShrink: 0, background: '#000' }}>
        {loading ? (
          <div style={{ width: '100%', height: 210, background: '#d1d5db', animation: 'pulse 1.5s ease-in-out infinite' }} />
        ) : error || !videoApi ? (
          <div style={{ width: '100%', height: 210, background: '#1f2937', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: '#9ca3af', fontSize: 13 }}>Video unavailable</span>
          </div>
        ) : (
          <iframe
            width="100%"
            height="210"
            src={`https://www.youtube.com/embed/${videoApi.video_id}?start=${startAt}&autoplay=${shouldAutoplay ? 1 : 0}`}
            title={videoApi.title}
            style={{ border: 'none', display: 'block' }}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            referrerPolicy="strict-origin-when-cross-origin"
            allowFullScreen
          />
        )}

        {/* Back arrow */}
        <button
          onClick={onBack}
          style={{
            position: 'absolute', top: 10, left: 10,
            background: 'rgba(0,0,0,0.45)',
            border: 'none', borderRadius: 20,
            width: 32, height: 32,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          <ChevronLeft size={20} color="white" />
        </button>
      </div>

      {/* ── Scrollable content ── */}
      <div style={{ flex: 1, overflowY: 'auto', background: 'white' }}>

        {/* Error state */}
        {error && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '32px 16px', gap: 12 }}>
            <p style={{ fontSize: 14, color: '#374151' }}>Could not load video. Please try again.</p>
            <button
              onClick={load}
              style={{
                padding: '8px 20px', background: '#5DCAA5', color: 'white',
                border: 'none', borderRadius: 8, fontSize: 13, cursor: 'pointer',
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div style={{ padding: '14px 16px', background: '#FAFAF8', display: 'flex', flexDirection: 'column', gap: 10 }}>
            <Skeleton width="55%" height={11} />
            <Skeleton width="85%" height={15} />
            <Skeleton width="70%" height={13} />
          </div>
        )}

        {/* Loaded content */}
        {!loading && !error && videoApi && (
          <>
            {/* Section 1 — Module header */}
            <div style={{ background: '#FAFAF8', padding: '14px 16px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 11, color: '#5DCAA5', fontWeight: 500, marginBottom: 2 }}>
                    {videoApi.subject_name}
                  </p>
                  <p style={{ fontSize: 15, fontWeight: 500, color: '#111827', lineHeight: 1.3 }}>
                    {videoApi.title}
                  </p>
                  {videoApi.lesson_name && (
                    <p style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
                      {videoApi.lesson_name}
                    </p>
                  )}
                </div>
                <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px 0 0 8px', flexShrink: 0 }}>
                  <Download size={20} color="#5DCAA5" />
                </button>
              </div>
            </div>

            <div style={{ height: 1, background: 'rgba(0,0,0,0.06)' }} />
          </>
        )}

        {/* Section 2 — Notes (only when not loading and there are pages) */}
        {!loading && notesPageCount > 0 && (
          <>
            <div style={{ padding: '12px 16px' }}>
              <button
                onClick={() => setNotesOpen(true)}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 12,
                  padding: '12px 14px',
                  background: 'white',
                  border: '1px solid rgba(0,0,0,0.1)',
                  borderRadius: 12,
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <div
                  style={{
                    width: 36, height: 36, borderRadius: 8,
                    background: '#E1F5EE',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <BookOpen size={18} color="#0F6E56" />
                </div>
                <span style={{ fontSize: 14, fontWeight: 500, color: '#111827', flex: 1 }}>
                  Notes ({notesPageCount} pages)
                </span>
              </button>
            </div>

            <div style={{ height: 1, background: 'rgba(0,0,0,0.06)' }} />
          </>
        )}

        {/* Section 3 — Chapters */}
        {!loading && (
          <>
            <div style={{ padding: '12px 16px 4px' }}>
              <p style={{ fontSize: 10, fontWeight: 500, color: '#9ca3af', letterSpacing: '0.07em', marginBottom: 8 }}>
                CHAPTERS
              </p>
              {mockVideoPage.chapters.map((ch, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    paddingTop: 10, paddingBottom: 10,
                    borderBottom: i < mockVideoPage.chapters.length - 1 ? '1px solid rgba(0,0,0,0.05)' : undefined,
                  }}
                >
                  <PlayCircle size={20} color="#5DCAA5" style={{ flexShrink: 0 }} />
                  <span style={{ flex: 1, fontSize: 13, color: '#1f2937' }}>{ch.title}</span>
                  <span style={{ fontSize: 12, color: '#9ca3af', fontVariantNumeric: 'tabular-nums' }}>
                    {ch.timestamp}
                  </span>
                </div>
              ))}
            </div>

            <div style={{ height: 1, background: 'rgba(0,0,0,0.06)', margin: '8px 0' }} />

            {/* Section 4 — Related Modules */}
            <div style={{ padding: '12px 16px 16px' }}>
              <p style={{ fontSize: 10, fontWeight: 500, color: '#9ca3af', letterSpacing: '0.07em', marginBottom: 10 }}>
                RELATED MODULES
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {mockVideoPage.relatedModules.map(mod => (
                  <div
                    key={mod.id}
                    style={{
                      display: 'flex', alignItems: 'flex-start', gap: 12,
                      padding: '12px',
                      background: 'white',
                      border: '1px solid rgba(0,0,0,0.08)',
                      borderRadius: 12,
                    }}
                  >
                    <div style={{ position: 'relative', flexShrink: 0 }}>
                      <div
                        style={{
                          width: 48, height: 48, borderRadius: 8,
                          background: mod.thumbnailColor,
                          border: '1px solid rgba(0,0,0,0.06)',
                        }}
                      />
                      {mod.progressPercent === 100 && (
                        <div style={{ position: 'absolute', top: -6, right: -6, background: 'white', borderRadius: '50%' }}>
                          <CheckCircle2 size={18} color="#5DCAA5" />
                        </div>
                      )}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p
                        style={{
                          fontSize: 13, fontWeight: 500, color: '#111827',
                          lineHeight: 1.35, marginBottom: 2,
                          display: '-webkit-box',
                          WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                        }}
                      >
                        {mod.title}
                      </p>
                      <p style={{ fontSize: 11, color: '#5DCAA5', marginBottom: 4 }}>{mod.subject}</p>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 2, fontSize: 11, color: '#6b7280' }}>
                          <Star size={10} color="#F9A825" fill="#F9A825" />
                          {mod.rating}
                        </span>
                        <span style={{ fontSize: 11, color: '#6b7280' }}>{mod.mcqCount} MCQs</span>
                        <span style={{ fontSize: 11, fontWeight: 500, color: mod.progressPercent === 100 ? '#5DCAA5' : '#378ADD' }}>
                          {mod.progressPercent}%
                        </span>
                      </div>
                      {mod.completedDate && (
                        <p style={{ fontSize: 10, color: '#9ca3af', marginTop: 3 }}>
                          Completed on {mod.completedDate}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ height: 72 }} />
          </>
        )}
      </div>

      {/* ── Sticky Mark Complete ── */}
      <div
        style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          padding: '10px 16px 14px',
          background: 'white',
          borderTop: '1px solid rgba(0,0,0,0.08)',
          boxShadow: '0 -4px 12px rgba(0,0,0,0.06)',
        }}
      >
        <button
          style={{
            width: '100%', height: 48,
            background: '#62C8DF', color: 'white',
            border: 'none', borderRadius: 12,
            fontSize: 13, fontWeight: 500,
            letterSpacing: '0.1em', textTransform: 'uppercase', cursor: 'pointer',
          }}
        >
          Mark Complete
        </button>
      </div>

      {notesOpen && (
        <NotesSheet
          notesImages={notesImages}
          subject={videoApi?.subject_name ?? result.subject}
          onClose={() => setNotesOpen(false)}
          initialMaximized={autoOpenNotes ?? false}
          initialPage={initialNotesPage}
        />
      )}
    </div>
  );
}
