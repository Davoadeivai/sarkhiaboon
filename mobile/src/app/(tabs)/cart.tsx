import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon } from '@/components/Icon';
import { Button, Card, Divider, EmptyState, ErrorState, Loading, Notice, T } from '@/components/ui';
import { isGuest, useAuth } from '@/lib/auth';
import { faDigits, toman } from '@/lib/format';
import { useCart, useRemoveItem, useSetQuantity } from '@/lib/queries';
import type { CartItem } from '@/lib/types';
import { colors, GUTTER, radius, space } from '@/theme/tokens';

function Stepper({ item, onError }: { item: CartItem; onError: (m: string) => void }) {
  const setQty = useSetQuantity();
  const remove = useRemoveItem();
  const busy = setQty.isPending || remove.isPending;
  const btn = (icon: 'plus' | 'minus' | 'trash', label: string, onPress: () => void, disabled = false) => (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={busy || disabled}
      onPress={onPress}
      hitSlop={6}
      style={{ width: 34, height: 34, alignItems: 'center', justifyContent: 'center', opacity: disabled ? 0.35 : 1 }}
    >
      <Icon name={icon} size={18} color={icon === 'trash' ? colors.danger : colors.ink} />
    </Pressable>
  );
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', borderWidth: 1.5, borderColor: colors.line, borderRadius: radius.pill, opacity: busy ? 0.6 : 1 }}>
      {btn('plus', 'یکی بیشتر', () => setQty.mutate({ itemId: item.id, quantity: item.quantity + 1 }, { onError: (e) => onError(e.message) }), item.quantity >= item.variant.stock)}
      <T variant="bodyStrong" style={{ minWidth: 22 }} center>
        {faDigits(item.quantity)}
      </T>
      {item.quantity > 1
        ? btn('minus', 'یکی کمتر', () => setQty.mutate({ itemId: item.id, quantity: item.quantity - 1 }, { onError: (e) => onError(e.message) }))
        : btn('trash', 'حذف از سبد', () => remove.mutate(item.id, { onError: (e) => onError(e.message) }))}
    </View>
  );
}

export default function CartScreen() {
  const insets = useSafeAreaInsets();
  const cart = useCart();
  const user = useAuth((s) => s.user);
  const [error, setError] = useState<string | null>(null);

  const c = cart.data;
  const empty = !c || c.items.length === 0;

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + space.md, paddingHorizontal: GUTTER, paddingBottom: space.xxl, gap: space.lg }}>
        <T variant="title" accessibilityRole="header">
          سبد خرید
        </T>

        {cart.isLoading ? (
          <Loading />
        ) : cart.error ? (
          <ErrorState message={cart.error.message} onRetry={() => cart.refetch()} />
        ) : empty ? (
          <EmptyState icon="bag" title="سبدت خالی است" body="لباسی را که پسندیدی اینجا اضافه کن." action="رفتن به ویترین" onAction={() => router.push('/')} />
        ) : (
          <>
            {c.items.map((item) => (
              <View key={item.id} style={{ flexDirection: 'row', gap: space.md, backgroundColor: colors.surface, borderRadius: radius.lg, padding: space.md, borderWidth: 1, borderColor: colors.line }}>
                <Pressable accessibilityRole="link" accessibilityLabel={item.variant.product_name} onPress={() => router.push(`/product/${item.variant.product_slug}`)}>
                  <View style={{ width: 76, height: 96, borderRadius: radius.md, overflow: 'hidden', backgroundColor: colors.porcelain }}>
                    {item.variant.image && <Image source={{ uri: item.variant.image }} style={{ width: 76, height: 96 }} contentFit="cover" />}
                  </View>
                </Pressable>
                <View style={{ flex: 1, justifyContent: 'space-between' }}>
                  <View>
                    <T variant="bodyStrong" numberOfLines={2}>
                      {item.variant.product_name}
                    </T>
                    <T variant="small" color={colors.mute}>
                      {[item.variant.size && `سایز ${item.variant.size}`, item.variant.color].filter(Boolean).join('، ')}
                    </T>
                  </View>
                  <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                    <T variant="smallStrong">{toman(item.line_total)}</T>
                    <Stepper item={item} onError={setError} />
                  </View>
                </View>
              </View>
            ))}

            {error && <Notice tone="error" text={error} />}

            <Card style={{ gap: space.sm }}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <T color={colors.mute}>جمع کالاها</T>
                <T>{toman(c.subtotal)}</T>
              </View>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <T color={colors.mute}>هزینه‌ی ارسال</T>
                <T color={c.shipping_cost ? colors.ink : colors.success}>{c.shipping_cost ? toman(c.shipping_cost) : 'رایگان'}</T>
              </View>
              <Divider style={{ marginVertical: space.xs }} />
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <T variant="bodyStrong">مبلغ قابل پرداخت</T>
                <T variant="heading">{toman(c.total)}</T>
              </View>
            </Card>
          </>
        )}
      </ScrollView>

      {!empty && (
        <View style={{ paddingHorizontal: GUTTER, paddingVertical: space.md, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.line, gap: space.xs }}>
          {isGuest(user) ? (
            <>
              <Button label="ورود و ادامه‌ی خرید" size="lg" onPress={() => router.push({ pathname: '/login', params: { next: '/checkout' } })} />
              <T variant="tiny" color={colors.mute} center>
                برای ثبت سفارش، شماره موبایلت را تأیید کن. سبد و کمدت حفظ می‌شود.
              </T>
            </>
          ) : (
            <Button label="ادامه‌ی خرید" size="lg" onPress={() => router.push('/checkout')} />
          )}
        </View>
      )}
    </View>
  );
}
