import React, { useState, useEffect, useRef } from 'react';

const FadeContent = ({ 
  children, 
  blur = false, 
  duration = 1000, 
  easing = "ease-out", 
  initialOpacity = 0,
  threshold = 0.1,
  delay = 0
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const elementRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            setIsVisible(true);
          }, delay);
        }
      },
      { threshold }
    );

    if (elementRef.current) {
      observer.observe(elementRef.current);
    }

    return () => {
      if (elementRef.current) {
        observer.unobserve(elementRef.current);
      }
    };
  }, [threshold, delay]);

  const style = {
    transition: `all ${duration}ms ${easing}`,
    opacity: isVisible ? 1 : initialOpacity,
    filter: blur 
      ? isVisible 
        ? 'blur(0px)' 
        : 'blur(10px)' 
      : 'none',
    transform: blur && !isVisible ? 'scale(0.95)' : 'scale(1)',
  };

  return (
    <div ref={elementRef} style={style}>
      {children}
    </div>
  );
};

export default FadeContent;