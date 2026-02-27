import { Button } from '@/components/ui/button';

function WelcomeImage() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-fg0 mb-4 size-16"
    >
      {/* Candlestick chart icon */}
      {/* Candle 1 – bearish (down) */}
      <line x1="12" y1="8" x2="12" y2="16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <rect x="8" y="16" width="8" height="14" rx="1" fill="currentColor" opacity="0.4" />
      <line x1="12" y1="30" x2="12" y2="38" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      {/* Candle 2 – bullish (up) */}
      <line x1="28" y1="12" x2="28" y2="20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <rect x="24" y="20" width="8" height="18" rx="1" fill="currentColor" />
      <line x1="28" y1="38" x2="28" y2="46" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      {/* Candle 3 – bearish */}
      <line x1="44" y1="6" x2="44" y2="14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <rect x="40" y="14" width="8" height="12" rx="1" fill="currentColor" opacity="0.4" />
      <line x1="44" y1="26" x2="44" y2="34" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      {/* Candle 4 – bullish */}
      <line x1="56" y1="18" x2="56" y2="24" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <rect x="52" y="24" width="8" height="20" rx="1" fill="currentColor" />
      <line x1="56" y1="44" x2="56" y2="52" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      {/* Baseline */}
      <line x1="4" y1="58" x2="60" y2="58" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
    </svg>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center">
        <WelcomeImage />

        <h1 className="text-foreground text-xl font-semibold tracking-tight">
          AI Trading Assistant
        </h1>
        <p className="text-muted-foreground max-w-xs pt-1 text-sm leading-6">
          Ask about your portfolio, analyse your trades, check live prices, or create a new pie — all by voice.
        </p>

        <Button
          size="lg"
          onClick={onStartCall}
          className="mt-6 w-64 rounded-full font-mono text-xs font-bold tracking-wider uppercase"
        >
          {startButtonText}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Powered by Trading 212 · For informational use only · Not financial advice.
        </p>
      </div>
    </div>
  );
};
