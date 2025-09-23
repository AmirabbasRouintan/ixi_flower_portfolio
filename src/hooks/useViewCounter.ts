import { useState, useEffect } from 'react';
import { incrementViewCount } from '../services/viewCounter';

/**
 * Custom hook to manage the view counter
 * @returns The current view count
 */
export const useViewCounter = () => {
  const [viewCount, setViewCount] = useState<number>(0);
  
  useEffect(() => {
    // Only increment the view count once when the component mounts
    const newCount = incrementViewCount();
    setViewCount(newCount);
  }, []);
  
  return viewCount;
};