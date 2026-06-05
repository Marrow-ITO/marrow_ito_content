import { useState } from 'react';
import { X, Maximize2, Minimize2, ChevronLeft, ChevronRight } from 'lucide-react';

type Props = {
  notesImages: string[];
  subject: string;
  onClose: () => void;
  initialMaximized?: boolean;
  initialPage?: number;
};

export default function NotesSheet({ notesImages, subject, onClose, initialMaximized, initialPage }: Props) {
  const [page, setPage] = useState(initialPage ? initialPage - 1 : 0);
  const [maximized, setMaximized] = useState(initialMaximized ?? false);
  const total = notesImages.length;

  return (
    /* Overlay backdrop */
    <div
      style={{
        position: 'absolute', inset: 0,
        background: maximized ? 'transparent' : 'rgba(0,0,0,0.45)',
        display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
        zIndex: 50,
      }}
      onClick={maximized ? undefined : onClose}
    >
      {/* Sheet */}
      <div
        style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          height: maximized ? '100%' : '75%',
          background: 'white',
          borderRadius: maximized ? 0 : '16px 16px 0 0',
          display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
          transition: 'height 0.3s ease-in-out, border-radius 0.3s ease-in-out',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex', alignItems: 'center',
            padding: '10px 14px',
            borderBottom: '1px solid rgba(0,0,0,0.08)',
            flexShrink: 0,
          }}
        >
          {/* Back chevron (only when maximized) */}
          {maximized && (
            <button
              onClick={() => setMaximized(false)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px 6px 4px 0', marginRight: 4 }}
            >
              <ChevronLeft size={20} color="#6b7280" />
            </button>
          )}

          {/* Page badge + subject */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
            <div
              style={{
                background: '#92400E', color: 'white',
                fontSize: 13, fontWeight: 500,
                padding: '2px 8px', borderRadius: 4,
                minWidth: 28, textAlign: 'center',
              }}
            >
              {page + 1}
            </div>
            <span style={{ fontSize: 13, color: '#6b7280' }}>{subject}</span>
          </div>

          {/* Close */}
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6 }}
          >
            <X size={18} color="#374151" />
          </button>

          {/* Maximize / Minimize toggle */}
          <button
            onClick={() => setMaximized(m => !m)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, marginLeft: 2 }}
          >
            {maximized
              ? <Minimize2 size={16} color="#9ca3af" />
              : <Maximize2 size={16} color="#9ca3af" />
            }
          </button>
        </div>

        {/* Image area */}
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative', background: '#FEFCE8' }}>
          <img
            src={notesImages[page]}
            alt={`Notes page ${page + 1}`}
            style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
          />

          {page > 0 && (
            <button
              onClick={() => setPage(p => p - 1)}
              style={{
                position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)',
                background: 'rgba(0,0,0,0.35)', border: 'none', borderRadius: '50%',
                width: 34, height: 34, display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer',
              }}
            >
              <ChevronLeft size={18} color="white" />
            </button>
          )}
          {page < total - 1 && (
            <button
              onClick={() => setPage(p => p + 1)}
              style={{
                position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
                background: 'rgba(0,0,0,0.35)', border: 'none', borderRadius: '50%',
                width: 34, height: 34, display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer',
              }}
            >
              <ChevronRight size={18} color="white" />
            </button>
          )}

          {/* Feedback label — left edge, vertical */}
          <div
            style={{
              position: 'absolute', left: -22, top: '50%',
              transform: 'translateY(-50%) rotate(-90deg)',
              background: '#F3F4F6', fontSize: 10, color: '#6b7280',
              padding: '3px 10px', borderRadius: 4,
              letterSpacing: '0.05em', whiteSpace: 'nowrap',
            }}
          >
            Feedback
          </div>
        </div>

        {/* Dot indicators */}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 6, padding: '8px 0 4px', flexShrink: 0 }}>
          {Array.from({ length: total }).map((_, i) => (
            <button
              key={i}
              onClick={() => setPage(i)}
              style={{
                width: i === page ? 18 : 6, height: 6, borderRadius: 3,
                background: i === page ? '#5DCAA5' : '#D1FAE5',
                border: 'none', cursor: 'pointer', padding: 0,
                transition: 'width 0.2s',
              }}
            />
          ))}
        </div>

        {/* Mark Complete button */}
        <div style={{ padding: '8px 16px 12px', flexShrink: 0 }}>
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
      </div>
    </div>
  );
}
