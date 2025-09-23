// Simple view counter service using localStorage
// In a production environment, this would be replaced with a proper backend API

const VIEW_COUNT_KEY = 'portfolio_view_count';

/**
 * Increment the view count by 1 and return the new count
 */
export const incrementViewCount = (): number => {
  // Get current count from localStorage
  const currentCount = getViewCount();
  
  // Increment by 1
  const newCount = currentCount + 1;
  
  // Save to localStorage
  localStorage.setItem(VIEW_COUNT_KEY, newCount.toString());
  
  return newCount;
};

/**
 * Get the current view count
 */
export const getViewCount = (): number => {
  const count = localStorage.getItem(VIEW_COUNT_KEY);
  return count ? parseInt(count, 10) : 0;
};