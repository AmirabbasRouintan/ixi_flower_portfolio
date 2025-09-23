"use client";

import { cn } from "@/lib/utils";
import { motion, useInView, type HTMLMotionProps } from "motion/react";
import React, { useEffect, useRef, useState } from "react";

interface TypingAnimationProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  className?: string;
  duration?: number;
  delay?: number;
  as?: React.ElementType;
  startOnView?: boolean;
}

export function TypingAnimation({
  children,
  className,
  duration = 15,
  delay = 0,
  as: Component = "div",
  startOnView = false,
  ...props
}: TypingAnimationProps) {
  const MotionComponent = motion.create(Component, {
    forwardMotionProps: true,
  });

  const [displayedContent, setDisplayedContent] = useState<React.ReactNode>(null);
  const [started, setStarted] = useState(false);
  const elementRef = useRef<HTMLElement | null>(null);
  const isInView = useInView(elementRef as React.RefObject<Element>, {
    amount: 0.3,
    once: true,
  });

  useEffect(() => {
    if (!startOnView) {
      const startTimeout = setTimeout(() => {
        setStarted(true);
      }, delay);
      return () => clearTimeout(startTimeout);
    }

    if (!isInView) return;

    const startTimeout = setTimeout(() => {
      setStarted(true);
    }, delay);

    return () => clearTimeout(startTimeout);
  }, [delay, startOnView, isInView]);

  useEffect(() => {
    if (!started) return;

    // Convert children to string for processing
    const textContent = React.Children.toArray(children)
      .map(child => {
        if (typeof child === 'string') return child;
        if (React.isValidElement(child)) {
          // For React elements, get their text content
          const element = child as React.ReactElement;
          const props = element.props as { children?: React.ReactNode };
          if (props && props.children) {
            return React.Children.toArray(props.children).join('');
          }
          return '';
        }
        return String(child);
      })
      .join('');

    const totalLength = textContent.length;
    let currentIndex = 0;

    const typingEffect = setInterval(() => {
      if (currentIndex <= totalLength) {
        // Build the content progressively
        const result = buildContentWithMarkup(children, currentIndex);
        setDisplayedContent(result);
        currentIndex++;
      } else {
        clearInterval(typingEffect);
      }
    }, duration);

    return () => {
      clearInterval(typingEffect);
    };
  }, [children, duration, started]);

  // Helper function to build content with HTML markup preserved
  function buildContentWithMarkup(children: React.ReactNode, maxChars: number): React.ReactNode {
    let charCount = 0;
    
    const processNode = (node: React.ReactNode): React.ReactNode => {
      if (typeof node === 'string') {
        if (charCount >= maxChars) return null;
        const remaining = maxChars - charCount;
        charCount += node.length;
        return node.slice(0, remaining);
      }
      
      if (React.isValidElement(node)) {
        const element = node as React.ReactElement;
        const props = element.props as { children?: React.ReactNode };
        const processedChildren = React.Children.map(
          props && props.children ? props.children : null, 
          processNode
        );
        
        if (processedChildren && processedChildren.some(child => child !== null)) {
          return React.cloneElement(element, {}, processedChildren);
        }
        return null;
      }
      
      return node;
    };

    return React.Children.map(children, processNode);
  }

  return (
    <MotionComponent
      ref={elementRef}
      className={cn(
        "text-1xl tracking-[-0.02em]",
        className,
      )}
      {...props}
    >
      {started ? displayedContent : null}
    </MotionComponent>
  );
}
