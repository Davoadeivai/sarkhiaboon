import { router } from 'expo-router';
import type { ReactNode } from 'react';
import { ScrollView, type ScrollViewProps, View, type ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, GUTTER, space } from '@/theme/tokens';
import { IconButton, T } from './ui';

/** Top bar for pushed screens: back button on the start (right) side, title, optional trailing action. */
export function ScreenHeader({ title, trailing, onBack }: { title?: string; trailing?: ReactNode; onBack?: () => void }) {
  const insets = useSafeAreaInsets();
  return (
    <View
      style={{
        paddingTop: insets.top + space.sm,
        paddingHorizontal: GUTTER,
        paddingBottom: space.sm,
        flexDirection: 'row',
        alignItems: 'center',
        gap: space.md,
        backgroundColor: colors.porcelain,
      }}
    >
      <IconButton
        name="back"
        label="بازگشت"
        onPress={onBack ?? (() => (router.canGoBack() ? router.back() : router.replace('/')))}
      />
      <T variant="heading" numberOfLines={1} style={{ flex: 1 }}>
        {title ?? ''}
      </T>
      {trailing}
    </View>
  );
}

/** Scrollable page body with the standard gutter and room for a bottom action bar. */
export function Page({
  children,
  bottomSpace = space.xxl,
  contentStyle,
  ...rest
}: ScrollViewProps & { children: ReactNode; bottomSpace?: number; contentStyle?: ViewStyle }) {
  return (
    <ScrollView
      {...rest}
      style={{ flex: 1, backgroundColor: colors.porcelain }}
      contentContainerStyle={[{ paddingHorizontal: GUTTER, paddingBottom: bottomSpace, gap: space.lg }, contentStyle]}
      keyboardShouldPersistTaps="handled"
    >
      {children}
    </ScrollView>
  );
}

/** Action bar pinned to the bottom of the screen, above the home indicator. */
export function BottomBar({ children }: { children: ReactNode }) {
  const insets = useSafeAreaInsets();
  return (
    <View
      style={{
        paddingHorizontal: GUTTER,
        paddingTop: space.md,
        paddingBottom: Math.max(insets.bottom, space.md),
        backgroundColor: colors.surface,
        borderTopWidth: 1,
        borderTopColor: colors.line,
        flexDirection: 'row',
        gap: space.md,
      }}
    >
      {children}
    </View>
  );
}
