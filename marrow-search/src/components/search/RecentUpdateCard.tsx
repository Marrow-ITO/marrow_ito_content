import { Zap, ExternalLink } from 'lucide-react';
import type { SearchResult } from '../../types';

type Props = { result: SearchResult };

function formatUpdateDate(dateStr?: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

function getSource(metadata?: string): string {
  if (!metadata) return '';
  const parts = metadata.split('·').map(p => p.trim());
  return parts.length >= 4 ? parts[parts.length - 1] : '';
}

export default function RecentUpdateCard({ result }: Props) {
  const source = getSource(result.metadata);
  const dateLabel = formatUpdateDate(result.date_of_update);

  return (
    <div
      style={{
        margin: '0 0 12px',
        borderRadius: 12,
        border: '1px solid #FDE68A',
        background: '#FFFBEB',
        padding: '12px 14px',
        borderLeft: '3px solid #F59E0B',
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <span
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 3,
            fontSize: 10, fontWeight: 500, letterSpacing: '0.06em',
            textTransform: 'uppercase', color: '#92400E',
          }}
        >
          <Zap size={11} />
          Recent Update
        </span>
        {dateLabel && (
          <span style={{ fontSize: 11, color: '#9ca3af' }}>· {dateLabel}</span>
        )}
      </div>

      {/* Title */}
      <p style={{ fontSize: 13, fontWeight: 500, color: '#1f2937', lineHeight: 1.4, marginBottom: result.snippet ? 4 : 0 }}>
        {result.title}
      </p>

      {/* Snippet */}
      {result.snippet && (
        <p
          style={{
            fontSize: 12, color: '#6b7280', marginBottom: source ? 4 : result.reference_link ? 10 : 0,
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}
        >
          {result.snippet}
        </p>
      )}

      {/* Source */}
      {source && (
        <p style={{ fontSize: 11, color: '#9ca3af', fontStyle: 'italic', marginBottom: result.reference_link ? 10 : 0 }}>
          {source}
        </p>
      )}

      {/* Read more */}
      {result.reference_link && (
        <a
          href={result.reference_link}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 3,
            fontSize: 12, fontWeight: 500, color: '#92400E',
            textDecoration: 'none',
          }}
        >
          Read more
          <ExternalLink size={11} />
        </a>
      )}
    </div>
  );
}
