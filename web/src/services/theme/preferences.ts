export type DesktopTheme = 'dark' | 'oled' | 'light';
export type DensityMode = 'standard' | 'compact';

export interface DesktopPreferences {
  theme?: string;
  densityMode?: string;
}

const validThemes = new Set<DesktopTheme>(['dark', 'oled', 'light']);
const validDensities = new Set<DensityMode>(['standard', 'compact']);

export function normalizeTheme(theme?: string): DesktopTheme {
  return validThemes.has(theme as DesktopTheme) ? theme as DesktopTheme : 'dark';
}

export function normalizeDensity(density?: string): DensityMode {
  return validDensities.has(density as DensityMode) ? density as DensityMode : 'standard';
}

export function applyDesktopPreferences(preferences: DesktopPreferences): void {
  if (typeof document === 'undefined') return;
  const theme = normalizeTheme(preferences.theme);
  const density = normalizeDensity(preferences.densityMode);
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.dataset.density = density;
  root.style.colorScheme = theme === 'light' ? 'light' : 'dark';
}
