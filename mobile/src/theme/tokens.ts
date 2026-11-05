/**
 * Sarkhiaboon design tokens.
 *
 * Concept: the shop window on the street corner. One bold motif — the Persian
 * arch (طاق) — marks everything that can be tried on: the fitting-room mirror,
 * try-on product cards and the result frame. Everything else stays quiet.
 */
export const colors = {
  ink: '#1C1A2B', // primary text, dark surfaces
  inkSoft: '#3A3750',
  mute: '#6E6B80', // secondary text
  faint: '#A3A1B2', // placeholders, disabled
  line: '#DFE1E8', // hairlines, input borders
  porcelain: '#F2F3F6', // app background
  surface: '#FFFFFF',
  firouzeh: '#0E7C7B', // primary action (turquoise tile)
  firouzehDeep: '#0A5E5D',
  firouzehMist: '#E3F1F0',
  saffron: '#E3A22B', // discounts and price highlights only
  anar: '#B3261E', // pomegranate red: the entry screens (splash, intro, login) — client's choice
  anarDeep: '#8E1D17',
  saffronMist: '#FBF0DA',
  danger: '#B4372F',
  dangerMist: '#F8E4E2',
  success: '#2E7D4F',
} as const;

export const fonts = {
  display: 'Lalezar_400Regular', // brand + screen titles (named after Tehran's Lalehzar shopping street)
  body: 'Vazirmatn_400Regular',
  medium: 'Vazirmatn_500Medium',
  bold: 'Vazirmatn_700Bold',
} as const;

/** Type scale (sizes in dp) with line heights tuned for Persian script. */
export const type = {
  hero: { fontFamily: fonts.display, fontSize: 40, lineHeight: 56 },
  title: { fontFamily: fonts.display, fontSize: 28, lineHeight: 40 },
  heading: { fontFamily: fonts.bold, fontSize: 18, lineHeight: 30 },
  body: { fontFamily: fonts.body, fontSize: 15, lineHeight: 26 },
  bodyStrong: { fontFamily: fonts.medium, fontSize: 15, lineHeight: 26 },
  small: { fontFamily: fonts.body, fontSize: 13, lineHeight: 22 },
  smallStrong: { fontFamily: fonts.medium, fontSize: 13, lineHeight: 22 },
  tiny: { fontFamily: fonts.medium, fontSize: 11, lineHeight: 18 },
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, xxxl: 48 } as const;

export const radius = { sm: 8, md: 14, lg: 20, pill: 999 } as const;

/** Page gutter used by every screen. */
export const GUTTER = 20;
