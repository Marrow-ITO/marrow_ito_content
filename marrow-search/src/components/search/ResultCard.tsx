import { Video, Clock, Search, BookOpen, Sparkles, Stethoscope, FileText } from 'lucide-react';
import { formatSeconds } from '../../lib/formatSeconds';
import type { SearchResult } from '../../types';

type Props = {
  result: SearchResult;
  onResultClick: (result: SearchResult) => void;
};

const TYPE_META: Record<SearchResult['type'], {
  Icon: typeof Video;
  label: string;
}> = {
  video:      { Icon: Video,        label: 'VIDEO'    },
  timestamp:  { Icon: Clock,        label: 'TIMESTAMP'},
  qbank:      { Icon: Search,       label: 'QBANK'    },
  module:     { Icon: BookOpen,     label: 'MODULE'   },
  pearl:      { Icon: Sparkles,     label: 'PEARL'    },
  clinical_q: { Icon: Stethoscope,  label: 'CLINICAL' },
  note:          { Icon: FileText,    label: 'NOTE'          },
  recent_update: { Icon: FileText,    label: 'RECENT UPDATE' },
};

export default function ResultCard({ result, onResultClick }: Props) {
  const meta = TYPE_META[result.type];
  const TypeIcon = meta.Icon;
  const isClickable = result.type === 'video' || result.type === 'timestamp' || result.type === 'note';

  return (
    <div
      style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px 14px', cursor: isClickable ? 'pointer' : 'default' }}
      onClick={isClickable ? () => onResultClick(result) : undefined}
    >
      {/* Thumbnail */}
      <div
        style={{
          width: 60, height: 48, borderRadius: 8,
          background: '#f3f4f6', border: '1px solid rgba(0,0,0,0.1)',
          flexShrink: 0, overflow: 'hidden',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        {result.thumbnail || result.thumbnail_url ? (
          <img
            src={result.thumbnail ?? result.thumbnail_url}
            alt={result.title}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <TypeIcon size={18} color="#9ca3af" />
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 13, fontWeight: 500, color: '#1f2937', lineHeight: 1.35, marginBottom: 2 }}>
          {result.title}
        </p>

        <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: result.snippet ? 3 : 5 }}>
          {result.subject}
          {result.metadata ? ` · ${result.metadata}` : ''}
        </p>

        {result.snippet && (
          <p style={{
            fontSize: 11, color: '#9ca3af', fontStyle: 'italic', marginBottom: 5,
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}>
            {result.snippet}
          </p>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, fontWeight: 500, color: '#6b7280', letterSpacing: '0.04em' }}>
            <TypeIcon size={10} />
            {meta.label}
          </span>

          {result.start_time !== undefined && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color: '#6b7280', background: '#f3f4f6', borderRadius: 999, padding: '2px 8px' }}>
              <Clock size={11} />
              {formatSeconds(result.start_time)}
            </span>
          )}

          {result.type === 'note' && result.page_no != null && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color: '#6b7280', background: '#f3f4f6', borderRadius: 999, padding: '2px 8px' }}>
              <FileText size={11} />
              Page {result.page_no}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
