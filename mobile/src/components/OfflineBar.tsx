import { useQueryClient } from '@tanstack/react-query';
import { Pressable, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useConnection } from '@/lib/offline';
import { colors, space } from '@/theme/tokens';

import { T } from './ui';

/** A thin strip at the top while the server is unreachable; the catalog keeps working from the saved copy. */
export function OfflineBar() {
  const offline = useConnection((s) => s.offline);
  const insets = useSafeAreaInsets();
  const qc = useQueryClient();
  if (!offline) return null;
  return (
    <View
      accessibilityRole="alert"
      style={{
        position: 'absolute', top: 0, start: 0, end: 0, zIndex: 50,
        paddingTop: insets.top + space.xs, paddingBottom: space.xs, paddingHorizontal: space.lg,
        backgroundColor: colors.ink, flexDirection: 'row', alignItems: 'center', gap: space.md,
      }}
    >
      <T variant="small" color={colors.surface} style={{ flex: 1 }}>
        بدون اینترنت؛ اطلاعات ذخیره‌شده را می‌بینی.
      </T>
      <Pressable
        accessibilityRole="button"
        hitSlop={8}
        onPress={() => qc.refetchQueries({ type: 'active' })}
      >
        <T variant="smallStrong" color={colors.firouzehMist}>تلاش دوباره</T>
      </Pressable>
    </View>
  );
}
