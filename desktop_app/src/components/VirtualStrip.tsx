import { useEffect, useRef } from 'react';
import { useLightingStore } from '../store/lightingStore';
import { DEFAULT_LED_COUNT } from '../types/lighting';

export const VirtualStrip = ({ ledCount: propLedCount }: { ledCount?: number }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const storeLedCount = useLightingStore(s => s.ledCount);
  const stripLedCount = propLedCount || storeLedCount || DEFAULT_LED_COUNT;

  useEffect(() => {
    // Subscribe directly to the store to prevent React re-renders at 20Hz
    const unsubscribe = useLightingStore.subscribe((state) => {
      if (containerRef.current) {
        // Set CSS variables on the container. 
        // The children divs will inherit and use these to render the colors using GPU acceleration.
        containerRef.current.style.setProperty('--v-rgb', `${state.color.r}, ${state.color.g}, ${state.color.b}`);
        containerRef.current.style.setProperty('--v-brightness', (state.renderBrightness / 100).toString());

        const dots = containerRef.current.querySelectorAll<HTMLDivElement>('.virtual-led-dot');
        if (state.ledFrame && Array.isArray(state.ledFrame) && state.ledFrame.length > 0) {
          const frame = state.ledFrame;
          const frameLen = frame.length;
          dots.forEach((dot, idx) => {
            const sampleIdx = Math.min(idx, frameLen - 1);
            const [r, g, b] = frame[sampleIdx];
            dot.style.backgroundColor = `rgb(${r}, ${g}, ${b})`;
            dot.style.boxShadow = (r > 10 || g > 10 || b > 10) ? `0 0 6px 2px rgba(${r}, ${g}, ${b}, 0.8)` : 'none';
          });
        } else {
          dots.forEach((dot) => {
            dot.style.backgroundColor = '';
            dot.style.boxShadow = '';
          });
        }
      }
    });

    return () => unsubscribe();
  }, []);

  // Display a representative slice of dots for high density strips
  const displayDots = Math.min(stripLedCount, 60);

  return (
    <div className="w-full mb-8">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold tracking-widest text-dev-text-secondary uppercase">Virtual Output</h3>
        <div className="text-[10px] text-dev-text-muted">{stripLedCount} LEDs</div>
      </div>
      
      <div 
        ref={containerRef}
        className="flex w-full items-center justify-between h-8 bg-black/40 rounded-lg border border-dev-border-light px-2 py-1 shadow-inner relative overflow-hidden"
        style={{ '--v-rgb': '0,0,0', '--v-brightness': '0' } as any}
      >
        {/* Glow backdrop layer for a premium look */}
        <div 
          className="absolute inset-0 opacity-80 blur-xl transition-all duration-75"
          style={{
            backgroundColor: 'rgba(var(--v-rgb), var(--v-brightness))'
          }}
        />

        {/* LED representation */}
        {Array.from({ length: displayDots }).map((_, i) => {
          const staticOpacity = 0.9 + (Math.sin(i * 0.5) * 0.1); 
          return (
            <div 
              key={i}
              className="virtual-led-dot w-1.5 h-1.5 rounded-full relative z-10 transition-colors duration-75"
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
