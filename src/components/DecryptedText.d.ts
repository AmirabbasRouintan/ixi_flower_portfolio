import { ReactNode } from 'react';

interface DecryptedTextProps {
  text: string;
  speed?: number;
  maxIterations?: number;
  sequential?: boolean;
  revealDirection?: 'start' | 'end' | 'random';
  useOriginalCharsOnly?: boolean;
  characters?: string;
  className?: string;
  parentClassName?: string;
  encryptedClassName?: string;
  animateOn?: 'hover' | 'mount' | 'scroll';
  [key: string]: any;
}

declare const DecryptedText: React.FC<DecryptedTextProps>;
export default DecryptedText;