type Props = {
  query: string;
  interpretedAs: string;
  relatedConcepts: string[];
  onChipClick?: (concept: string) => void;
};

export default function InterpretationCard({ query, interpretedAs, relatedConcepts, onChipClick }: Props) {
  const isSameAsQuery = interpretedAs?.toLowerCase() === query?.toLowerCase();
  const hasInterpretation = !isSameAsQuery && Boolean(interpretedAs);
  const hasRelatedConcepts = relatedConcepts && relatedConcepts.length > 0;

  if (!hasInterpretation && !hasRelatedConcepts) return null;

  return (
    <div
      style={{
        background: '#E6F1FB',
        borderRadius: 12,
        padding: '12px 14px',
        marginBottom: 12,
        border: '1px solid rgba(55,138,221,0.15)',
      }}
    >
      {hasInterpretation && (
        <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.45 }}>
          Showing results for{' '}
          <span style={{ color: '#378ADD' }}>"{query}"</span>
          {' · '}understood as{' '}
          <strong style={{ fontWeight: 500, color: '#1f2937' }}>{interpretedAs}</strong>
        </p>
      )}

      {hasRelatedConcepts && (
        <>
          <p style={{ fontSize: 11, color: '#9ca3af', marginTop: hasInterpretation ? 8 : 0, marginBottom: 6 }}>
            Also pulling related concepts:
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {relatedConcepts.map(c => (
              <button
                key={c}
                type="button"
                onClick={() => onChipClick?.(c)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: 12,
                  fontWeight: 500,
                  color: '#0F6E56',
                  background: '#E1F5EE',
                  border: '1px solid rgba(15,110,86,0.2)',
                  padding: '3px 10px',
                  borderRadius: 999,
                  cursor: onChipClick ? 'pointer' : 'default',
                }}
              >
                ↳ {c}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
