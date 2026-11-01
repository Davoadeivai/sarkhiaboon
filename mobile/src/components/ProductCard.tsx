import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Pressable, View } from 'react-native';

import { faNumber } from '@/lib/format';
import type { ProductListItem } from '@/lib/types';
import { colors, radius, space } from '@/theme/tokens';
import { Arch } from './Arch';
import { Icon } from './Icon';
import { DiscountTag, Price, T } from './ui';

/**
 * Product tile. Products the customer can try on get the arch shape and a
 * small arch badge; everything else is a plain rounded rectangle — so the
 * shape itself tells the shopper what they can try on.
 */
export function ProductCard({ product, width }: { product: ProductListItem; width: number }) {
  const height = Math.round(width * 1.3);
  const image = product.image ? (
    <Image source={{ uri: product.image }} style={{ width, height }} contentFit="cover" transition={200} />
  ) : null;

  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`${product.name}، ${faNumber(product.price)} تومان${product.supports_tryon ? '، قابل پرو' : ''}`}
      onPress={() => router.push(`/product/${product.slug}`)}
      style={({ pressed }) => ({ width, opacity: pressed ? 0.85 : 1 })}
    >
      <View>
        {product.supports_tryon ? (
          <Arch width={width} height={height}>
            {image}
          </Arch>
        ) : (
          <View style={{ width, height, borderRadius: radius.md, overflow: 'hidden', backgroundColor: colors.porcelain }}>{image}</View>
        )}
        {!product.in_stock && (
          <View style={{ position: 'absolute', bottom: 8, start: 8, end: 8, backgroundColor: 'rgba(28,26,43,0.78)', borderRadius: radius.sm, paddingVertical: 2 }}>
            <T variant="tiny" color="#FFFFFF" center>
              ناموجود
            </T>
          </View>
        )}
        {product.supports_tryon && (
          <View
            style={{
              position: 'absolute',
              bottom: 8,
              end: 8,
              width: 30,
              height: 30,
              borderRadius: 15,
              backgroundColor: colors.surface,
              alignItems: 'center',
              justifyContent: 'center',
              display: product.in_stock ? 'flex' : 'none',
            }}
          >
            <Icon name="arch" size={18} color={colors.firouzeh} />
          </View>
        )}
      </View>
      <View style={{ paddingTop: space.sm, gap: 2 }}>
        <T variant="small" numberOfLines={1}>
          {product.name}
        </T>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
          <DiscountTag percent={product.discount_percent} />
          <Price price={product.price} compareAt={product.compare_at_price} />
        </View>
      </View>
    </Pressable>
  );
}
