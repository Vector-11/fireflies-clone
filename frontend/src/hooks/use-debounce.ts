"use client";

import * as React from "react";

/**
 * Delay a rapidly changing value.
 *
 * Used by the search inputs so a request is fired once the user pauses rather
 * than once per keystroke. The timer is cleared on every change, which is what
 * makes it a debounce rather than a throttle.
 */
export function useDebounce<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = React.useState(value);

  React.useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
