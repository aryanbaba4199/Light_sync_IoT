import React, { useEffect, useRef } from 'react';
import { useLightingStore } from '../store/lightingStore';

export const VirtualStrip = ({ ledCount = 60 }: { ledCount?: number }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Subscribe directly to the store to prevent React re-renders at 20Hz
    const unsubscribe = useLightingStore.subscribe((state) => {
      if (containerRef.current) {
        // Set CSS variables on the container. 
        // The children divs will inherit and use these to render the colors using GPU acceleration.
        containerRef.current.style.setProperty('--v-rgb', `${state.color.r}, ${state.color.g}, ${state.color.b}`);
        containerRef.current.style.setProperty('--v-brightness', (state.renderBrightness / 100).toString());
      }
    });

    return () => unsubscribe();
  }, []);

  return (
    <div className="w-full mb-8">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold tracking-widest text-dev-text-secondary uppercase">Virtual Output</h3>
        <div className="text-[10px] text-dev-text-muted">60 LEDs</div>
      </div>
      
      <div 
        ref={containerRef}
        className="flex w-full items-center justify-between h-8 bg-black/40 rounded-lg border border-dev-border-light px-2 py-1 shadow-inner relative overflow-hidden"
        style={{ '--v-rgb': '0,0,0', '--v-brightness': '0' } as React.CSSProperties}
      >
        {/* Glow backdrop layer for a premium look */}
        <div 
          className="absolute inset-0 opacity-80 blur-xl transition-all duration-75"
          style={{
            backgroundColor: 'rgba(var(--v-rgb), var(--v-brightness))'
          }}
        />

        {/* 60 individual LEDs */}
        {Array.from({ length: ledCount }).map((_, i) => {
          // Keep a very slight variation so it looks like LEDs, but keep it very bright (0.9 - 1.0)
          const staticOpacity = 0.9 + (Math.sin(i * 0.5) * 0.1); 
          return (
            <div 
              key={i}
              className="w-1.5 h-1.5 rounded-full relative z-10 transition-colors duration-75"
              style={{
                backgroundColor: 'rgba(var(--v-rgb), var(--v-brightness))',
                boxShadow: '0 0 6px 2px rgba(var(--v-rgb), var(--v-brightness))',
                opacity: staticOpacity
              }}
            />
          );
        })}
      </div>
    </div>
  );
};
