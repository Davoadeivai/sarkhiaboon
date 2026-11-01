import { Image } from 'expo-image';
import { useState } from 'react';
import { FlatList, Pressable, ScrollView, View } from 'react-native';

import { openLink } from '@/lib/links';
import type { Banner, ProductListItem, Shortcut } from '@/lib/types';
import { colors, GUTTER, radius, space } from '@/theme/tokens';
import { ProductCard } from './ProductCard';
import { T } from './ui';

export function BannerCarousel({ banners, width }: { banners: Banner[]; width: number }) {
  const [page, setPage] = useState(0);
  const itemW = width - GUTTER * 2;
  const height = Math.round(itemW * 0.5);
  if (!banners.length) return null;
  return (
    <View style={{ gap: space.sm }}>
      <FlatList
        horizontal
        data={banners}
        keyExtractor={(b) => String(b.id)}
        showsHorizontalScrollIndicator={false}
        snapToInterval={itemW + space.md}
        decelerationRate="fast"
        contentContainerStyle={{ paddingHorizontal: GUTTER, gap: space.md }}
        onScroll={(e) => setPage(Math.round(Math.abs(e.nativeEvent.contentOffset.x) / (itemW + space.md)))}
        scrollEventThrottle={32}
        renderItem={({ item }) => (
          <Pressable
            accessibilityRole={item.link.type === 'none' ? 'image' : 'link'}
            accessibilityLabel={item.title}
            onPress={() => openLink(item.link)}
            style={{ width: itemW, height, borderRadius: radius.lg, overflow: 'hidden', backgroundColor: colors.line }}
          >
            <Image source={{ uri: item.image }} style={{ width: itemW, height }} contentFit="cover" transition={250} />
          </Pressable>
        )}
      />
      {banners.length > 1 && (
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 6 }} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
          {banners.map((b, i) => (
            <View
              key={b.id}
              style={{ width: i === page ? 18 : 6, height: 6, borderRadius: 3, backgroundColor: i === page ? colors.ink : colors.line }}
            />
          ))}
        </View>
      )}
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
