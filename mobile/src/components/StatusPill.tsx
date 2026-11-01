import { View } from 'react-native';

import { colors, radius } from '@/theme/tokens';
import { T } from './ui';

const TONES: Record<string, { bg: string; fg: string }> = {
  pending_payment: { bg: colors.saffronMist, fg: '#7A5410' },
  paid: { bg: colors.firouzehMist, fg: colors.firouzehDeep },
  processing: { bg: colors.firouzehMist, fg: colors.firouzehDeep },
  shipped: { bg: colors.ink, fg: '#FFFFFF' },
  delivered: { bg: '#E3F2E9', fg: colors.success },
  cancelled: { bg: colors.porcelain, fg: colors.mute },
  expired: { bg: colors.porcelain, fg: colors.mute },
};

export function StatusPill({ status, label }: { status: string; label: string }) {
  const t = TONES[status] ?? TONES.cancelled;
  return (
    <View style={{ backgroundColor: t.bg, borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 2 }}>
      <T variant="tiny" color={t.fg}>
        {label}
      </T>
    </View>
  );
}
