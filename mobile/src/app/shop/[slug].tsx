import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useMemo } from 'react';
import { ScrollView, useWindowDimensions, View } from 'react-native';

import { ArchImage } from '@/components/Arch';
import { ProductGrid } from '@/components/home';
import { ProductCard } from '@/components/ProductCard';
import { ScreenHeader } from '@/components/Screen';
import { Button, DiscountTag, ErrorState, Loading, Price, SectionHeader, T } from '@/components/ui';
import { faDigits } from '@/lib/format';
import { useProduct, useProducts, useShop } from '@/lib/queries';
import { colors, GUTTER, radius, space } from '@/theme/tokens';

/**
 * A registered shop. Opened from a product: the chosen item sits on top with
 * «پرو کن», followed by the shop's other items in the same category, then the rest.
 */
export default function ShopScreen() {
  const { slug, product: productSlug } = useLocalSearchParams<{ slug: string; product?: string }>();
  const { width } = useWindowDimensions();
  const shop = useShop(slug);
  const selected = useProduct(productSlug ?? '');
  const items = useProducts({ shop: slug, ordering: '-created_at' });

  const all = useMemo(() => items.data?.pages.flatMap((p) => p.results) ?? [], [items.data]);
  const chosen = productSlug ? selected.data : undefined;
  const sameCategory = all.filter((p) => p.slug !== productSlug && chosen && p.category.id === chosen.category.id);
  const others = all.filter((p) => p.slug !== productSlug && !sameCategory.includes(p));

  // Tapping another item of this shop keeps you here and brings it to the top.
  const pick = (s: string) => router.setParams({ product: s });

  if (shop.isLoading) return <Loading />;
  if (shop.error || !shop.data)
    return (
      <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
        <ScreenHeader title="فروشگاه" />
        <ErrorState message={shop.error?.message ?? 'این فروشگاه پیدا نشد.'} onRetry={() => shop.refetch()} />
      </View>
    );

  const s = shop.data;
  const coverW = width - GUTTER * 2;
  const heroW = Math.min(coverW, 360);
  const cardW = Math.floor((width - GUTTER * 2 - space.md) / 2);

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader title={s.name} />
      <ScrollView contentContainerStyle={{ paddingBottom: space.xxxl, gap: space.xl }}>
        <View style={{ paddingHorizontal: GUTTER }}>
          <View style={{ borderRadius: radius.lg, overflow: 'hidden', backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line }}>
            {s.cover && <Image source={{ uri: s.cover }} style={{ width: coverW, height: Math.round(coverW * 0.34) }} contentFit="cover" />}
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md, padding: space.lg }}>
              <View style={{ width: 56, height: 56, borderRadius: 28, overflow: 'hidden', backgroundColor: colors.porcelain, borderWidth: 2, borderColor: colors.surface, marginTop: -36 }}>
                {s.logo && <Image source={{ uri: s.logo }} style={{ width: 52, height: 52 }} contentFit="cover" />}
              </View>
              <View style={{ flex: 1 }}>
                <T variant="bodyStrong">{s.name}</T>
                <T variant="small" color={colors.mute}>
                  {[s.city, `${faDigits(s.product_count)} کالا`].filter(Boolean).join('، ')}
                </T>
              </View>
            </View>
            {!!s.description && (
              <T variant="small" color={colors.inkSoft} style={{ paddingHorizontal: space.lg, paddingBottom: space.lg }}>
                {s.description}
              </T>
            )}
          </View>
        </View>

        {chosen && (
          <View style={{ paddingHorizontal: GUTTER, alignItems: 'center', gap: space.md }}>
            {chosen.supports_tryon ? (
              <ArchImage uri={chosen.image} width={heroW} height={Math.round(heroW * 1.25)} label={chosen.name} />
            ) : (
              <View style={{ width: heroW, height: Math.round(heroW * 1.25), borderRadius: radius.lg, overflow: 'hidden', backgroundColor: colors.line }}>
                {chosen.image && <Image source={{ uri: chosen.image }} style={{ width: heroW, height: Math.round(heroW * 1.25) }} contentFit="cover" />}
              </View>
            )}
            <View style={{ alignSelf: 'stretch', gap: space.xs }}>
              <T variant="title">{chosen.name}</T>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
                <Price price={chosen.price} compareAt={chosen.compare_at_price} size="lg" />
                <DiscountTag percent={chosen.discount_percent} />
              </View>
            </View>
            <View style={{ alignSelf: 'stretch', flexDirection: 'row', gap: space.md }}>
              {chosen.supports_tryon && (
                <Button
                  label="پرو کن"
                  icon="arch"
                  size="lg"
                  style={{ flex: 1 }}
                  onPress={() => router.push({ pathname: '/tryon/[slug]', params: { slug: chosen.slug } })}
                />
              )}
              <Button
                label="سایز و خرید"
                icon="bag"
                tone="outline"
                size="lg"
                style={{ flex: 1 }}
                onPress={() => router.push(`/product/${chosen.slug}`)}
              />
            </View>
          </View>
        )}

        {sameCategory.length > 0 && (
          <View>
            <SectionHeader title={`${chosen?.category.name ?? ''} دیگر این فروشگاه`} />
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: GUTTER, columnGap: space.md, rowGap: space.xl }}>
              {sameCategory.map((p) => (
                <ProductCard key={p.id} product={p} width={cardW} onPress={() => pick(p.slug)} />
              ))}
            </View>
          </View>
        )}

        {others.length > 0 && (
          <View>
            <SectionHeader title={chosen ? 'سایر محصولات این فروشگاه' : 'محصولات این فروشگاه'} />
            <ProductGridPick products={others} width={width} onPick={pick} />
          </View>
        )}
        {items.isLoading && <Loading />}
      </ScrollView>
    </View>
  );
}

function ProductGridPick({ products, width, onPick }: { products: Parameters<typeof ProductGrid>[0]['products']; width: number; onPick: (slug: string) => void }) {
  const cardW = Math.floor((width - GUTTER * 2 - space.md) / 2);
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: GUTTER, columnGap: space.md, rowGap: space.xl }}>
      {products.map((p) => (
        <ProductCard key={p.id} product={p} width={cardW} onPress={() => onPick(p.slug)} />
      ))}
    </View>
  );
}
