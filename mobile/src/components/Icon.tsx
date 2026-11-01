import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { colors } from '@/theme/tokens';

/**
 * Hand-drawn line icon set (24×24, 1.75 stroke). Kept in-house so the whole
 * app shares one stroke weight and the arch glyph matches the arch frames.
 * Directional icons are drawn for RTL: "back" points right, "forward" left.
 */
const paths = {
  home: ['M3 10.5 4.6 5h14.8L21 10.5', 'M4.5 10.5V20h15v-9.5', 'M3 10.5h18', 'M9.5 20v-5.5h5V20'],
  grid: [],
  closet: ['M12 8.6V7.7c0-.6.3-1 .8-1.3A2.1 2.1 0 1 0 9.9 4.5', 'M12 8.6 3.4 14.7c-.9.6-.5 2 .6 2h16c1.1 0 1.5-1.4.6-2L12 8.6Z'],
  bag: ['M5 8h14l-1.2 12H6.2L5 8Z', 'M9 10V6.5a3 3 0 0 1 6 0V10'],
  user: ['M5 20c1.2-3.5 3.9-5.2 7-5.2s5.8 1.7 7 5.2'],
  heart: ['M12 19.5s-7.2-4.3-7.2-9.8A4 4 0 0 1 12 7.3a4 4 0 0 1 7.2 2.4c0 5.5-7.2 9.8-7.2 9.8Z'],
  back: ['m9.5 6 6 6-6 6'],
  forward: ['m14.5 6-6 6 6 6'],
  camera: ['M4 8.5h3.2L9 6h6l1.8 2.5H20V19H4V8.5Z'],
  image: ['M4 5h16v14H4z', 'm4 16 4.5-4.5 3.5 3.5 2.5-2.5L20 18'],
  share: ['M12 4v11', 'm8 8 4-4 4 4', 'M5 13v6h14v-6'],
  check: ['m5 12.5 4.5 4.5L19 7.5'],
  plus: ['M12 5v14', 'M5 12h14'],
  minus: ['M5 12h14'],
  close: ['m6 6 12 12', 'M18 6 6 18'],
  trash: ['M5 7h14', 'M9.5 7V5h5v2', 'M6.5 7l.8 12h9.4l.8-12'],
  search: ['m16 16 4 4'],
  arch: ['M6 20v-8.5a6 6 0 0 1 12 0V20', 'M4 20h16'],
  sort: ['M4 7h16', 'M7 12h10', 'M10 17h4'],
  box: ['M4 8l8-4 8 4v8l-8 4-8-4V8Z', 'M4 8l8 4 8-4', 'M12 12v8'],
  pin: ['M12 21s-6-5.6-6-10.5a6 6 0 0 1 12 0C18 15.4 12 21 12 21Z'],
  lock: ['M6 11h12v9H6z', 'M8.5 11V8a3.5 3.5 0 0 1 7 0v3'],
  logout: ['M14 5h5v14h-5', 'M10 8l-4 4 4 4', 'M6 12h9'],
  sun: ['M12 3v2', 'M12 19v2', 'M3 12h2', 'M19 12h2', 'm5.6 5.6 1.4 1.4', 'm17 17 1.4 1.4', 'm5.6 18.4 1.4-1.4', 'm17 7 1.4-1.4'],
  person: ['M12 9v6', 'M8 11.5l4-1.5 4 1.5', 'M10 21l2-6 2 6'],
  wall: ['M4 4h16v16H4z', 'M4 9.5h16', 'M4 14.5h16', 'M10 4v5.5', 'M14 9.5v5', 'M10 14.5V20'],
  refresh: ['M19 8a7.5 7.5 0 1 0 .5 6', 'M19.5 4v4.5H15'],
} as const;

export type IconName = keyof typeof paths;

interface Props {
  name: IconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
  filled?: boolean;
}

export function Icon({ name, size = 24, color = colors.ink, strokeWidth = 1.75, filled = false }: Props) {
  const common = { stroke: color, strokeWidth, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {name === 'grid' && (
        <>
          <Rect x={4} y={4} width={6.5} height={6.5} rx={1.5} {...common} />
          <Rect x={13.5} y={4} width={6.5} height={6.5} rx={1.5} {...common} />
          <Rect x={4} y={13.5} width={6.5} height={6.5} rx={1.5} {...common} />
          <Rect x={13.5} y={13.5} width={6.5} height={6.5} rx={1.5} {...common} />
        </>
      )}
      {name === 'user' && <Circle cx={12} cy={8.2} r={3.6} {...common} />}
      {name === 'camera' && <Circle cx={12} cy={13.4} r={3.4} {...common} />}
      {name === 'image' && <Circle cx={15.5} cy={9} r={1.5} {...common} />}
      {name === 'search' && <Circle cx={10.8} cy={10.8} r={6} {...common} />}
      {name === 'pin' && <Circle cx={12} cy={10.5} r={2.2} {...common} />}
      {name === 'sun' && <Circle cx={12} cy={12} r={3.6} {...common} />}
      {name === 'person' && <Circle cx={12} cy={5.5} r={2} {...common} />}
      {paths[name].map((d) => (
        <Path key={d} d={d} {...common} fill={filled && name === 'heart' ? color : 'none'} />
      ))}
    </Svg>
  );
}
