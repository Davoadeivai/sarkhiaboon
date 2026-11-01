import { useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect } from 'react';
import { View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Arch } from '@/components/Arch';
import { Icon } from '@/components/Icon';
import { Button, T } from '@/components/ui';
import { keys } from '@/lib/queries';
import { colors, GUTTER, space } from '@/theme/tokens';

/** Landing screen after the bank (deep link sarkhiaboon://payment/result?order=…&status=…). */
export default function PaymentResult() {
  const { order, status } = useLocalSearchParams<{ order?: string; status?: string }>();
  const insets = useSafeAreaInsets();
  const qc = useQueryClient();
  const ok = status === 'success';

  useEffect(() => {
    qc.invalidateQueries({ queryKey: keys.orders });
    qc.invalidateQueries({ queryKey: keys.cart });
    if (order) qc.invalidateQueries({ queryKey: keys.order(order) });
  }, [qc, order]);

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain, paddingTop: insets.top + space.xxxl, paddingHorizontal: GUTTER, alignItems: 'center', gap: space.lg }}>
      <Arch width={120} height={156} background={ok ? colors.firouzeh : colors.dangerMist} style={{ alignItems: 'center', justifyContent: 'center' }}>
        <Icon name={ok ? 'check' : 'close'} size={52} color={ok ? '#FFFFFF' : colors.danger} strokeWidth={2.2} />
      </Arch>
      <T variant="title" center accessibilityRole="header">
        {ok ? 'سفارشت ثبت شد' : 'پرداخت انجام نشد'}
      </T>
      <T color={colors.mute} center style={{ maxWidth: 320 }}>
        {ok
          ? `شماره‌ی سفارش ${order ?? ''}. وضعیت ارسال را از بخش سفارش‌ها دنبال کن.`
          : 'اگر مبلغی از حسابت کم شده، حداکثر تا ۷۲ ساعت به حسابت برمی‌گردد. کالاها هنوز تا پایان مهلت برایت رزرو هستند.'}
      </T>
      <View style={{ alignSelf: 'stretch', gap: space.md, marginTop: space.lg }}>
        {order && (
          <Button label={ok ? 'پیگیری سفارش' : 'دوباره پرداخت کن'} size="lg" onPress={() => router.replace({ pathname: '/orders/[number]', params: { number: order } })} />
        )}
        <Button label="بازگشت به ویترین" tone="outline" size="lg" onPress={() => router.replace('/')} />
      </View>
    </View>
  );
}
