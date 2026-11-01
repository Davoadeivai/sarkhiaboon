/**
 * Demo runtime switch. In normal builds this stub is used and the demo is off.
 * For the browser demo (EXPO_PUBLIC_DEMO=1), metro.config.js swaps this file
 * for runtime.demo.ts, which answers API calls in the browser with sample data.
 */
type DemoApi = (path: string, method: string, body: unknown) => Promise<{ status: number; data: unknown }>;

export const DEMO = false;
export const demoApi: DemoApi | null = null;
export const demoFonts: Record<string, string> | null = null;
