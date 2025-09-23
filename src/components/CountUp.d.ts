import { ReactNode } from 'react';

interface CountUpProps {
  to: number;
  from?: number;
  direction?: 'up' | 'down';
  delay?: number;
  duration?: number;
  className?: string;
  startWhen?: boolean;
  separator?: string;
  onStart?: () => void;
  onEnd?: () => void;
  useShiny?: boolean;
  shinySpeed?: number;
}

declare const CountUp: React.FC<CountUpProps>;
export default CountUp;