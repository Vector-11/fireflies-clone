"use client";

import * as React from "react";

/**
 * Read a query-string parameter on the client.
 *
 * Next's `useSearchParams()` forces the calling component into a Suspense
 * boundary that has to be resolved during streaming. Every page in this app
 * fetches its data client-side through React Query, so there is nothing for the
 * server to stream into that boundary — it just adds a failure mode, and in
 * practice left the page rendering its fallback forever.
 *
 * Reading `location` directly keeps these as plain client components. The value
 * is populated in an effect rather than during the first render so the server
 * and client agree on the initial markup; `popstate` keeps it correct across
 * browser back and forward.
 */
export function useQueryParam(name: string): string | null {
  const [value, setValue] = React.useState<string | null>(null);

  React.useEffect(() => {
    const read = () => new URLSearchParams(window.location.search).get(name);
    setValue(read());

    const onPopState = () => setValue(read());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [name]);

  return value;
}
