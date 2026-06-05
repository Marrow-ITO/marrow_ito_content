import type { ReactNode } from 'react';

export default function MobileFrame({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div
        className="relative bg-white overflow-hidden flex flex-col shadow-2xl"
        style={{
          width: 380,
          height: 820,
          borderRadius: 32,
          border: '10px solid #111',
        }}
      >
        {children}
      </div>
    </div>
  );
}
