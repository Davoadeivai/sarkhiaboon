import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, useWindowDimensions, View } from 'react-native';

import { ArchImage } from '@/components/Arch';
import { BottomBar, ScreenHeader } from '@/components/Screen';
import { Button, Chip, DiscountTag, ErrorState, IconButton, Loading, Notice, Price, T } from '@/components/ui';
import { faDigits } from '@/lib/format';
import { useAddToCart, useProduct, useToggleFavorite } from '@/lib/queries';
import type { ProductVariant } from '@/lib/types';
import { colors, GUTTER, radius, space } from '@/theme/tokens';

const TRYON_LABEL: Record<string, string> = {
  upper_body: 'بالاتنه',
  lower_body: 'پایین‌تنه',
  dresses: 'لباس یک‌تکه',
};

export default function ProductScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const { width } = useWindowDimensions();
  const product = useProduct(slug);
  const fav = useToggleFavorite();
  const addToCart = useAddToCart();

  const [imageIndex, setImageIndex] = useState(0);
  const [size, setSize] = useState<string | null>(null);
  const [color, setColor] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; tone: 'info' | 'error' } | null>(null);

  const p = product.data;
  const sizes = useMemo(() => [...new Set(p?.variants.map((v) => v.size).filter(Boolean))], [p]);
  const colorsList = useMemo(() => {
    const seen = new Map<string, ProductVariant>();
    p?.variants.forEach((v) => v.color && !seen.has(v.color) && seen.set(v.color, v));
    return [...seen.values()];
  }, [p]);

  // Pre-select when there is only one option, so a one-size item is one tap to buy.
  useEffect(() => {
    if (sizes.length === 1) setSize(sizes[0]);
    if (colorsList.length === 1) setColor(colorsList[0].color);
  }, [sizes, colorsList]);

  if (product.isLoading) return <Loading />;
  if (product.error || !p)
    return (
      <View style={{ flex: 1 }}>
        <ScreenHeader />
        <ErrorState message={product.error?.message ?? 'محصول پیدا نشد.'} onRetry={() => product.refetch()} />
      </View>
    );

  const gallery = [p.image, ...p.images.map((i) => i.image)].filter(Boolean) as string[];
  const heroW = width - GUTTER * 2;
  const heroH = Math.round(heroW * 1.25);
  const variant = p.variants.find(
    (v) => (!sizes.length || v.size === size) && (!colorsList.length || v.color === color),
  );
  const sizeAvailable = (s: string) => p.variants.some((v) => v.size === s && v.in_stock && (!color || v.color === color));

  const onAdd = () => {
    setMessage(null);
    if (!variant) {
      setMessage({ text: sizes.length && !size ? 'اول سایز را انتخاب کن.' : 'اول رنگ را انتخاب کن.', tone: 'error' });
      return;
    }
    addToCart.mutate(
      { variantId: variant.id },
      {
        onSuccess: () => setMessage({ text: 'به سبد اضافه شد.', tone: 'info' }),
        onError: (e) => setMessage({ text: e.message, tone: 'error' }),
      },
    );
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader
        title=""
        trailing={
          <IconButton
            name="heart"
            label={p.is_favorite ? 'حذف از علاقه‌مندی‌ها' : 'افزودن به علاقه‌مندی‌ها'}
            filled={p.is_favorite}
            color={p.is_favorite ? colors.danger : colors.ink}
            onPress={() => fav.mutate({ productId: p.id, on: !p.is_favorite })}
          />
        }
      />
      <ScrollView contentContainerStyle={{ paddingBottom: space.xxl, gap: space.xl }}>
        <View style={{ paddingHorizontal: GUTTER, gap: space.md }}>
          {p.supports_tryon ? (
            <ArchImage uri={gallery[imageIndex]} width={heroW} height={heroH} label={p.name} />
          ) : (
            <View style={{ width: heroW, height: heroH, borderRadius: radius.lg, overflow: 'hidden', backgroundColor: colors.line }}>
              {gallery[imageIndex] && (
                <Image source={{ uri: gallery[imageIndex] }} style={{ width: heroW, height: heroH }} contentFit="cover" transition={200} accessibilityLabel={p.name} />
              )}
            </View>
          )}
          {gallery.length > 1 && (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }}>
              {gallery.map((uri, i) => (
                <Pressable
                  key={uri + i}
                  accessibilityRole="button"
                  accessibilityLabel={`تصویر ${faDigits(i + 1)}`}
                  onPress={() => setImageIndex(i)}
                  style={{
                    width: 56,
                    height: 70,
                    borderRadius: radius.sm,
                    overflow: 'hidden',
                    borderWidth: 2,
                    borderColor: i === imageIndex ? colors.ink : 'transparent',
                  }}
                >
                  <Image source={{ uri }} style={{ width: '100%', height: '100%' }} contentFit="cover" />
                </Pressable>
              ))}
            </ScrollView>
          )}
        </View>

        <View style={{ paddingHorizontal: GUTTER, gap: space.sm }}>
          <T variant="small" color={colors.mute}>
            {p.category.name}
          </T>
          <T variant="title" accessibilityRole="header">
            {p.name}
          </T>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
            <Price price={variant?.price ?? p.price} compareAt={p.compare_at_price} size="lg" />
            <DiscountTag percent={p.discount_percent} />
          </View>
        </View>

        {p.supports_tryon && (
          <View style={{ marginHorizontal: GUTTER }}>
            <Notice text={`قابل پرو روی عکس خودت (${TRYON_LABEL[p.tryon_type] ?? 'لباس'}). قبل از خرید ببین به تو می‌آید یا نه.`} />
          </View>
        )}

        {colorsList.length > 0 && (
          <View style={{ paddingHorizontal: GUTTER, gap: space.sm }}>
            <T variant="bodyStrong">رنگ</T>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
              {colorsList.map((v) => (
                <Chip key={v.color} label={v.color} swatch={v.color_hex || undefined} active={color === v.color} onPress={() => setColor(v.color)} />
              ))}
            </View>
          </View>
        )}

        {sizes.length > 0 && (
          <View style={{ paddingHorizontal: GUTTER, gap: space.sm }}>
            <T variant="bodyStrong">سایز</T>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
              {sizes.map((s) => {
                const ok = sizeAvailable(s);
                return (
                  <Pressable
                    key={s}
                    accessibilityRole="button"
                    accessibilityLabel={`سایز ${s}${ok ? '' : '، ناموجود'}`}
                    accessibilityState={{ selected: size === s, disabled: !ok }}
                    disabled={!ok}
                    onPress={() => setSize(s)}
                    style={{
                      minWidth: 52,
                      height: 46,
                      paddingHorizontal: space.md,
                      borderRadius: radius.md,
                      borderWidth: 1.5,
                      borderColor: size === s ? colors.ink : colors.line,
                      backgroundColor: size === s ? colors.ink : colors.surface,
                      alignItems: 'center',
                      justifyContent: 'center',
                      opacity: ok ? 1 : 0.4,
                    }}
                  >
                    <T variant="bodyStrong" color={size === s ? '#FFFFFF' : colors.ink} style={!ok ? { textDecorationLine: 'line-through' } : undefined}>
                      {s}
                    </T>
                  </Pressable>
                );
              })}
            </View>
            {variant && variant.in_stock && variant.stock <= 3 && (
              <T variant="small" color={colors.danger}>{`فقط ${faDigits(variant.stock)} عدد باقی مانده.`}</T>
            )}
          </View>
        )}

        {!!p.description && (
          <View style={{ paddingHorizontal: GUTTER, gap: space.sm }}>
            <T variant="bodyStrong">توضیحات</T>
            <T color={colors.inkSoft}>{p.description}</T>
          </View>
        )}

        {message && (
          <View style={{ paddingHorizontal: GUTTER }}>
            <Notice text={message.text} tone={message.tone} />
          </View>
        )}
      </ScrollView>

      <BottomBar>
        {p.supports_tryon && (
          <Button
            label="پرو کن"
            icon="arch"
            size="lg"
            style={{ flex: 1 }}
            onPress={() => router.push({ pathname: '/tryon/[slug]', params: { slug: p.slug } })}
          />
        )}
        <Button
          label={p.in_stock ? 'افزودن به سبد' : 'ناموجود'}
          tone={p.supports_tryon ? 'outline' : 'ink'}
          icon="bag"
          size="lg"
          style={{ flex: 1 }}
          disabled={!p.in_stock}
          loading={addToCart.isPending}
          onPress={onAdd}
        />
      </BottomBar>
    </View>
  );
}
