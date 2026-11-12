import { useEffect, useState } from 'react';

export function useCountdown(initialSeconds = 0) {
  const [secondsLeft, setSecondsLeft] = useState<number>(initialSeconds);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = window.setInterval(() => {
      setSecondsLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [secondsLeft]);

  const startCountdown = (seconds: number) => {
    setSecondsLeft(Math.max(0, Math.floor(seconds)));
  };

  return {
    secondsLeft,
    isActive: secondsLeft > 0,
    startCountdown,
  };
}
