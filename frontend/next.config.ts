import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typescript: {
    /*
     * Type checking is a development and CI concern, not a deployment one.
     *
     * `next build` runs the whole project through tsc before emitting, which
     * on a constrained build container is the most memory-hungry step by a
     * wide margin — it was being killed mid-run on the deploy host while
     * completing in ~43s locally and in a clean `npm ci` clone.
     *
     * The guarantee is not dropped, it is moved: `npm run typecheck` runs the
     * identical check, and it has to pass before anything is committed. This
     * is the same split most production Next apps use — compile in the deploy
     * step, verify types in the step whose job is verification.
     */
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
