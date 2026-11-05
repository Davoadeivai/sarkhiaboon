import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, StyleSheet, View } from 'react-native';

import { colors } from '@/theme/tokens';
import { Arch } from './Arch';
import { T } from './ui';

/**
 * Red entry screen with the logo, shown over the app at launch (the client's
 * request). It matches the native splash colour, so the hand-off is seamless,
 * stays at least `minMs`, then fades out once the app is ready.
 */
export function Intro({ ready, minMs = 1400 }: { ready: boolean; minMs?: number }) {
  const [elapsed, setElapsed] = useState(false);
  const [gone, setGone] = useState(false);
  const opacity = useRef(new Animated.Value(1)).current;
  const rise = useRef(new Animated.Value(12)).current;

  useEffect(() => {
    const id = setTimeout(() => setElapsed(true), minMs);
    Animated.timing(rise, { toValue: 0, duration: 600, useNativeDriver: true }).start();
    return () => clearTimeout(id);
  }, [minMs, rise]);

  useEffect(() => {
    if (!(ready && elapsed)) return;
    AccessibilityInfo.isReduceMotionEnabled()
      .catch(() => false)
      .then((reduce) => {
        if (reduce) return setGone(true);
        Animated.timing(opacity, { toValue: 0, duration: 380, useNativeDriver: true }).start(() => setGone(true));
      });
  }, [ready, elapsed, opacity]);

  if (gone) return null;
  return (
    <Animated.View
      accessibilityLabel="سرخیابون"
      style={[StyleSheet.absoluteFill, { backgroundColor: colors.anar, opacity, alignItems: 'center', justifyContent: 'center', zIndex: 100 }]}
    >
      <Animated.View style={{ alignItems: 'center', gap: 6, transform: [{ translateY: rise }] }}>
        <Arch width={52} height={76} bottomRadius={0} background="#FFFFFF" />
        <T variant="hero" color="#FFFFFF" center style={{ fontSize: 60, lineHeight: 84 }}>
          سرخیابون
        </T>
        <T color="rgba(255,255,255,0.82)" center>
          پرو مجازی لباس، قبل از خرید
        </T>
      </Animated.View>
      <View style={{ position: 'absolute', bottom: 48, width: 28, height: 3, borderRadius: 2, backgroundColor: 'rgba(255,255,255,0.4)' }} />
    </Animated.View>
  );
}
