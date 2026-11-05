import { Image, type ImageProps } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { type ReactNode, useEffect, useRef } from 'react';
import { AccessibilityInfo, Animated, Easing, StyleSheet, View, type ViewStyle } from 'react-native';

import { colors } from '@/theme/tokens';

/**
 * The arch (طاق) — the app's one signature shape. It only frames things that
 * can be tried on: try-on product cards, the fitting-room mirror and results.
 */
export function Arch({
  width,
  height,
  children,
  style,
  background = colors.porcelain,
  bottomRadius = 6,
}: {
  width: number;
  height: number;
  children?: ReactNode;
  style?: ViewStyle;
  background?: string;
  bottomRadius?: number;
}) {
  const r = width / 2;
  return (
    <View
      style={[
        {
          width,
          height,
          borderTopLeftRadius: r,
          borderTopRightRadius: r,
          borderBottomLeftRadius: bottomRadius,
          borderBottomRightRadius: bottomRadius,
          overflow: 'hidden',
          backgroundColor: background,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function ArchImage({
  uri,
  width,
  height,
  contentFit = 'cover',
  label,
}: {
  uri: string | null | undefined;
  width: number;
  height: number;
  contentFit?: ImageProps['contentFit'];
  label?: string;
}) {
  return (
    <Arch width={width} height={height}>
      {uri ? (
        <Image
          source={{ uri }}
          style={{ width, height }}
          contentFit={contentFit}
          transition={250}
          accessibilityLabel={label}
          accessible={!!label}
        />
      ) : null}
    </Arch>
  );
}

/**
 * The fitting-room mirror: a double-lined arch (like a tiled portal) with a
 * soft glass sheen. While `scanning`, a band of turquoise light sweeps down
 * the glass — the app's single orchestrated motion, shown while the GPU works.
 */
export function Mirror({
  uri,
  width,
  scanning = false,
  dim = false,
  label,
  children,
}: {
  uri: string | null | undefined;
  width: number;
  scanning?: boolean;
  dim?: boolean;
  label?: string;
  children?: ReactNode;
}) {
  const frame = 8;
  const outerH = Math.round(width * 1.42);
  const innerW = width - frame * 2;
  const innerH = outerH - frame * 2;
  const sweep = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!scanning) return;
    let loop: Animated.CompositeAnimation | undefined;
    let cancelled = false;
    AccessibilityInfo.isReduceMotionEnabled()
      .catch(() => false)
      .then((reduce) => {
        if (cancelled || reduce) return;
        sweep.setValue(0);
        loop = Animated.loop(
          Animated.timing(sweep, { toValue: 1, duration: 2200, easing: Easing.inOut(Easing.cubic), useNativeDriver: true }),
        );
        loop.start();
      });
    return () => {
      cancelled = true;
      loop?.stop();
    };
  }, [scanning, sweep]);

  const band = innerH * 0.35;
  const translateY = sweep.interpolate({ inputRange: [0, 1], outputRange: [-band, innerH] });

  return (
    <Arch width={width} height={outerH} background={colors.surface} style={{ borderWidth: 1, borderColor: colors.line, padding: frame - 1 }}>
      <Arch width={innerW} height={innerH} background={colors.ink}>
        {uri ? (
          <Image
            source={{ uri }}
            style={{ width: innerW, height: innerH, opacity: dim ? 0.55 : 1 }}
            contentFit="cover"
            cachePolicy="memory"
            transition={400}
            accessibilityLabel={label}
            accessible={!!label}
          />
        ) : null}
        <LinearGradient
          pointerEvents="none"
          colors={['rgba(255,255,255,0.22)', 'rgba(255,255,255,0)']}
          start={{ x: 1, y: 0 }}
          end={{ x: 0.35, y: 0.45 }}
          style={StyleSheet.absoluteFill}
        />
        {scanning && (
          <Animated.View pointerEvents="none" style={{ position: 'absolute', left: 0, right: 0, height: band, transform: [{ translateY }] }}>
            <LinearGradient
              colors={['rgba(14,124,123,0)', 'rgba(64,201,198,0.55)', 'rgba(14,124,123,0)']}
              style={{ flex: 1 }}
            />
          </Animated.View>
        )}
        {children}
      </Arch>
    </Arch>
  );
}
