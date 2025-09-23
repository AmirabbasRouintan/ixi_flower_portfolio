import { useEffect, useRef, useState } from 'react';
import { useInView, useMotionValue, useSpring } from 'motion/react';
import ShinyText from './ShinyText';

export default function CountUp({
  to,
  from = 0,
  direction = 'up',
  delay = 0,
  duration = 2,
  className = '',
  startWhen = true,
  separator = '',
  onStart,
  onEnd,
  useShiny = true,
  shinySpeed = 3
}) {
  const ref = useRef(null);
  const [displayValue, setDisplayValue] = useState(String(direction === 'down' ? to : from));
  const motionValue = useMotionValue(direction === 'down' ? to : from);

  const damping = 20 + 40 * (1 / duration);
  const stiffness = 100 * (1 / duration);

  const springValue = useSpring(motionValue, {
    damping,
    stiffness
  });

  const isInView = useInView(ref, { once: true, margin: '0px' });

  const getDecimalPlaces = num => {
    const str = num.toString();

    if (str.includes('.')) {
      const decimals = str.split('.')[1];

      if (parseInt(decimals) !== 0) {
        return decimals.length;
      }
    }

    return 0;
  };

  const maxDecimals = Math.max(getDecimalPlaces(from), getDecimalPlaces(to));

  useEffect(() => {
    if (!useShiny && ref.current) {
      ref.current.textContent = String(direction === 'down' ? to : from);
    } else {
      setDisplayValue(String(direction === 'down' ? to : from));
    }
  }, [from, to, direction, useShiny]);

  useEffect(() => {
    if (isInView && startWhen) {
      if (typeof onStart === 'function') onStart();

      const timeoutId = setTimeout(() => {
        motionValue.set(direction === 'down' ? from : to);
      }, delay * 1000);

      const durationTimeoutId = setTimeout(
        () => {
          if (typeof onEnd === 'function') onEnd();
        },
        delay * 1000 + duration * 1000
      );

      return () => {
        clearTimeout(timeoutId);
        clearTimeout(durationTimeoutId);
      };
    }
  }, [isInView, startWhen, motionValue, direction, from, to, delay, onStart, onEnd, duration]);

  useEffect(() => {
    const unsubscribe = springValue.on('change', latest => {
      const hasDecimals = maxDecimals > 0;

      const options = {
        useGrouping: !!separator,
        minimumFractionDigits: hasDecimals ? maxDecimals : 0,
        maximumFractionDigits: hasDecimals ? maxDecimals : 0
      };

      const formattedNumber = Intl.NumberFormat('en-US', options).format(latest);
      const formattedText = separator ? formattedNumber.replace(/,/g, separator) : formattedNumber;
      
      if (!useShiny && ref.current) {
        ref.current.textContent = formattedText;
      } else {
        setDisplayValue(formattedText);
      }
    });

    return () => unsubscribe();
  }, [springValue, separator, maxDecimals, useShiny]);

  if (useShiny) {
    return (
      <div className={className} ref={ref}>
        <ShinyText text={displayValue} speed={shinySpeed} />
      </div>
    );
  }

  return <span className={className} ref={ref} />;
}
