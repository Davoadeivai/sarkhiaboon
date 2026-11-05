import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, FlatList, PanResponder, Pressable, ScrollView, View } from 'react-native';

import { faDigits } from '@/lib/format';
import { openLink } from '@/lib/links';
import type { Banner, ProductListItem, Shortcut } from '@/lib/types';
import { colors, GUTTER, radius, space } from '@/theme/tokens';
import { ProductCard } from './ProductCard';
import { T } from './ui';

/**
 * Slider of up to a few banners: one slide at a time, advances by itself every
 * few seconds, swipe or tap the dots to change. (One slide in view instead of a
 * scrolled strip keeps it identical on Android, iOS and the web in RTL.)
 */
export function BannerCarousel({
  banners,
  width,
  interval = 4500,
  height: fixedHeight,
}: {
  banners: Banner[];
  width: number;
  interval?: number;
  height?: number;
}) {
  const [page, setPage] = useState(0);
  const [reduceMotion, setReduceMotion] = useState(false);
  const fade = useRef(new Animated.Value(1)).current;
  const paused = useRef(false);
  const itemW = width - GUTTER * 2;
  const height = fixedHeight ?? Math.round(itemW * 0.5);
  const count = banners.length;

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion).catch(() => {});
  }, []);

  const go = useCallback(
    (next: number) => {
      const target = (next + count) % count;
      if (reduceMotion) {
        setPage(target);
        return;
      }
      Animated.timing(fade, { toValue: 0.15, duration: 160, useNativeDriver: true }).start(() => {
        setPage(target);
        Animated.timing(fade, { toValue: 1, duration: 260, useNativeDriver: true }).start();
      });
    },
    [count, fade, reduceMotion],
  );

  useEffect(() => {
    if (count < 2) return;
    const id = setInterval(() => {
      if (!paused.current) go(page + 1);
    }, interval);
    return () => clearInterval(id);
  }, [count, go, interval, page]);

  // Swipe: in RTL, swiping toward the right shows the next slide.
  const pan = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 12 && Math.abs(g.dx) > Math.abs(g.dy),
        onPanResponderGrant: () => {
          paused.current = true;
        },
        onPanResponderRelease: (_, g) => {
          paused.current = false;
          if (g.dx > 40) go(page + 1);
          else if (g.dx < -40) go(page - 1);
        },
        onPanResponderTerminate: () => {
          paused.current = false;
        },
      }),
    [go, page],
  );

  if (!count) return null;
  const item = banners[Math.min(page, count - 1)];
  return (
    <View style={{ gap: space.sm, paddingHorizontal: GUTTER }}>
      <View {...pan.panHandlers}>
        <Pressable
          accessibilityRole={item.link.type === 'none' ? 'image' : 'link'}
          accessibilityLabel={item.title}
          accessibilityHint={count > 1 ? `اسلاید ${faDigits(page + 1)} از ${faDigits(count)}` : undefined}
          onPress={() => openLink(item.link)}
          style={{ width: itemW, height, borderRadius: radius.lg, overflow: 'hidden', backgroundColor: colors.line }}
        >
          <Animated.View style={{ flex: 1, opacity: fade }}>
            <Image source={{ uri: item.image }} style={{ width: itemW, height }} contentFit="cover" transition={200} />
          </Animated.View>
        </Pressable>
      </View>
      {count > 1 && (
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 6 }}>
          {banners.map((b, i) => (
            <Pressable
              key={b.id}
              accessibilityRole="button"
              accessibilityLabel={`اسلاید ${faDigits(i + 1)}`}
              accessibilityState={{ selected: i === page }}
              hitSlop={8}
              onPress={() => go(i)}
              style={{ width: i === page ? 18 : 6, height: 6, borderRadius: 3, backgroundColor: i === page ? colors.ink : colors.line }}
            />
          ))}
        </View>
      )}
    </View>
  );
}

/** Photo tiles for clothing categories (home) and subcategories (category page). */
export function CategoryTiles({
  categories,
  width,
  columns = 3,
}: {
  categories: { id: number; name: string; slug: string; image: string | null }[];
  width: number;
  columns?: number;
}) {
  const tileW = Math.floor((width - GUTTER * 2 - space.md * (columns - 1)) / columns);
  const tileH = Math.round(tileW * 1.22);
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: GUTTER, columnGap: space.md, rowGap: space.lg }}>
      {categories.map((c) => (
        <Pressable
          key={c.id}
          accessibilityRole="link"
          accessibilityLabel={c.name}
          onPress={() => router.push({ pathname: '/category/[slug]', params: { slug: c.slug } })}
          style={({ pressed }) => ({ width: tileW, gap: space.xs, opacity: pressed ? 0.85 : 1 })}
        >
          <View style={{ width: tileW, height: tileH, borderRadius: radius.md, overflow: 'hidden', backgroundColor: colors.line }}>
            {c.image && <Image source={{ uri: c.image }} style={{ width: tileW, height: tileH }} contentFit="cover" transition={200} />}
          </View>
          <T variant={columns <= 2 ? 'bodyStrong' : 'smallStrong'} center numberOfLines={1}>
            {c.name}
          </T>
        </Pressable>
      ))}
    </View>
  );
}

/** The employer's promotional icons: round tiles that jump to a category, product or link. */
export function ShortcutRow({ shortcuts }: { shortcuts: Shortcut[] }) {
  if (!shortcuts.length) return null;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: GUTTER, gap: space.lg }}>
      {shortcuts.map((s) => (
        <Pressable
          key={s.id}
          accessibilityRole="link"
          accessibilityLabel={s.title}
          onPress={() => openLink(s.link)}
          style={{ width: 68, alignItems: 'center', gap: space.xs }}
        >
          <View
            style={{
              width: 64,
              height: 64,
              borderRadius: 32,
              backgroundColor: colors.surface,
              borderWidth: 1,
              borderColor: colors.line,
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
            }}
          >
            <Image source={{ uri: s.icon }} style={{ width: 40, height: 40 }} contentFit="contain" />
          </View>
          <T variant="tiny" center numberOfLines={1} color={colors.inkSoft}>
            {s.title}
          </T>
        </Pressable>
      ))}
    </ScrollView>
  );
}

export function ProductRail({ products, cardWidth = 148 }: { products: ProductListItem[]; cardWidth?: number }) {
  return (
    <FlatList
      horizontal
      data={products}
      keyExtractor={(p) => String(p.id)}
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ paddingHorizontal: GUTTER, gap: space.md }}
      renderItem={({ item }) => <ProductCard product={item} width={cardWidth} />}
    />
  );
}

export function ProductGrid({ products, width }: { products: ProductListItem[]; width: number }) {
  const cardW = Math.floor((width - GUTTER * 2 - space.md) / 2);
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: GUTTER, columnGap: space.md, rowGap: space.xl }}>
      {products.map((p) => (
        <ProductCard key={p.id} product={p} width={cardW} />
      ))}
    </View>
  );
}
