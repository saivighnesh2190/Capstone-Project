import evidence from "@/data/cp2-static.json";

export const CP2_STATIC = evidence as {
  project: string;
  cp2_primary: boolean;
  scenarios: Array<Record<string, unknown>>;
  benchmark: {
    fixtures: Array<Record<string, unknown>>;
    totals: Record<string, Record<string, unknown>>;
  };
  simulations: Record<string, Record<string, unknown>>;
  validate: { passed: boolean; output: string; stderr: string };
};

/**
 * Vercel's Node runtime does not include the Python interpreter or the local
 * repository fixtures. The static CP-2 evidence bundle keeps the public demo
 * truthful and interactive without pretending that Vercel is running the
 * local Python simulator.
 */
export function isStaticEvidence() {
  return process.env.VERCEL === "1" || process.env.NEXT_PUBLIC_CP2_STATIC === "1";
}

export function staticSimulation(fixture: string, policy: string) {
  return CP2_STATIC.simulations[`${fixture}:${policy}`] ?? null;
}
