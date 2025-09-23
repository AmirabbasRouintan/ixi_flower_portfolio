import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const AnimatedContent = ({
  children,
  distance = 0,
  direction = 'vertical',
  reverse = false,
  duration = 1,
  ease = 'power3.out',
  initialOpacity = 1,
  animateOpacity = false,
  scale = 1,
  threshold = 0.1,
  delay = 0,
  className = '',
  once = true,
  ...props
}) => {
  const elementRef = useRef(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    // Set initial state
    gsap.set(element, {
      opacity: initialOpacity,
      scale: scale,
    });

    // Apply initial position based on direction
    if (direction === 'horizontal') {
      gsap.set(element, {
        x: reverse ? distance : -distance,
      });
    } else {
      gsap.set(element, {
        y: reverse ? distance : -distance,
      });
    }

    // Create animation
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: element,
        start: `top bottom-=${threshold * 100}%`,
        toggleActions: once ? 'play none none none' : 'play none none reverse',
        once: once,
      },
    });

    // Add animation to timeline
    tl.to(
      element,
      {
        x: 0,
        y: 0,
        opacity: animateOpacity ? 1 : initialOpacity,
        scale: 1,
        duration: duration,
        delay: delay,
        ease: ease,
      },
      0
    );

    return () => {
      tl.kill();
      if (!once) {
        ScrollTrigger.getAll().forEach(trigger => trigger.kill());
      }
    };
  }, [
    distance,
    direction,
    reverse,
    duration,
    ease,
    initialOpacity,
    animateOpacity,
    scale,
    threshold,
    delay,
    once,
  ]);

  return (
    <div ref={elementRef} className={className} {...props}>
      {children}
    </div>
  );
};

export default AnimatedContent;