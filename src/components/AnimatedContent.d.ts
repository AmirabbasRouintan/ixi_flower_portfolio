import { ReactNode } from 'react';

interface AnimatedContentProps {
  children: ReactNode;
  distance?: number;
  direction?: 'vertical' | 'horizontal';
  reverse?: boolean;
  duration?: number;
  ease?: string;
  initialOpacity?: number;
  animateOpacity?: boolean;
  scale?: number;
  threshold?: number;
  delay?: number;
  className?: string;
  once?: boolean;
  [key: string]: any;
}

declare const AnimatedContent: React.FC<AnimatedContentProps>;
export default AnimatedContent;