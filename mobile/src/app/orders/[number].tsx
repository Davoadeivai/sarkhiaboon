import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { Page, ScreenHeader } from '@/components/Screen';
import { StatusPill } from '@/components/StatusPill';
import { Button, Card, Divider, ErrorState, Loading, Notice, T } from '@/components/ui';
import { faDate, faDigits, faPhone, toman } from '@/lib/format';
import { payOrder } from '@/lib/payment';
import { useCancelOrder, useOrder } from '@/lib/queries';
import { colors, space } from '@/theme/tokens';

const STEPS = [
  { key: 'paid', label: 'پرداخت‌شده' },
  { key: 'processing', label: 'در حال آماده‌سازی' },
  { key: 'shipped', label: 'ارسال‌شده' },
  { key: 'delivered', label: 'تحویل‌شده' },
];

export default function OrderScreen() {
  const { number } = useLocalSearchParams<{ number: string }>();
  const order = useOrder(number);
  const cancel = useCancelOrder();
  const [error, setError] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);

  if (order.isLoading) return <Loading />;
  const o = order.data;
  if (!o)
    return (
      <View style={{ flex: 1 }}>
        <ScreenHeader title="سفارش" />
        <ErrorState message={order.error?.message ?? 'سفارش پیدا نشد.'} onRetry={() => order.refetch()} />
      </View>
    );

  const stepIndex = STEPS.findIndex((s) => s.key === o.status);
  const pending = o.status === 'pending_payment';

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader title={`سفارش ${o.number}`} />
      <Page>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <T color={colors.mute}>{faDate(o.created_at)}</T>
          <StatusPill status={o.status} label={o.status_label} />
        </View>

        {stepIndex >= 0 && (
          <Card style={{ gap: space.md }}>
            {/* A real sequence, so numbered steps are meaningful here. */}
            {STEPS.map((s, i) => {
              const reached = i <= stepIndex;
              return (
                <View key={s.key} style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
                  <View
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: 13,
                      backgroundColor: reached ? colors.firouzeh : colors.porcelain,
                      borderWidth: 1.5,
                      borderColor: reached ? colors.firouzeh : colors.line,
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <T variant="tiny" color={reached ? '#FFFFFF' : colors.faint}>
                      {faDigits(i + 1)}
                    </T>
                  </View>
                  <T variant={i === stepIndex ? 'bodyStrong' : 'body'} color={reached ? colors.ink : colors.faint}>
                    {s.label}
                  </T>
                </View>
              );
            })}
            {!!o.tracking_code && <Notice text={`کد رهگیری مرسوله: ${o.tracking_code}`} />}
          </Card>
        )}

        {pending && (
          <Notice
            tone="warn"
            text={`پرداخت این سفارش هنوز انجام نشده.${o.reserved_until ? ' کالاها تا چند دقیقه‌ی دیگر برایت رزرو هستند.' : ''}`}
          />
        )}

        <Card style={{ gap: space.md }}>
          {o.items.map((it, idx) => (
            <View key={idx} style={{ flexDirection: 'row', justifyContent: 'space-between', gap: space.md }}>
              <View style={{ flex: 1 }}>
                <T variant="bodyStrong">{it.product_name}</T>
                <T variant="small" color={colors.mute}>
                  {`${it.variant_label}، ${faDigits(it.quantity)} عدد`}
                </T>
              </View>
              <T variant="smallStrong">{toman(it.line_total)}</T>
            </View>
          ))}
          <Divider />
          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
            <T color={colors.mute}>ارسال</T>
            <T>{o.shipping_cost ? toman(o.shipping_cost) : 'رایگان'}</T>
          </View>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
            <T variant="bodyStrong">جمع کل</T>
            <T variant="heading">{toman(o.total)}</T>
          </View>
        </Card>

        <Card style={{ gap: 2 }}>
          <T variant="bodyStrong">{o.recipient_name}</T>
          <T variant="small" color={colors.mute}>{`${o.province}، ${o.city}، ${o.address}`}</T>
          <T variant="small" color={colors.mute}>{`کد پستی ${faDigits(o.postal_code)}، ${faPhone(o.recipient_phone)}`}</T>
        </Card>

        {error && <Notice tone="error" text={error} />}

        {pending && (
          <View style={{ gap: space.md }}>
            <Button
              label={`پرداخت ${toman(o.total)}`}
              size="lg"
              loading={paying}
              onPress={async () => {
                setError(null);
                setPaying(true);
                try {
                  await payOrder(o.number);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setPaying(false);
                }
              }}
            />
            <Button
              label="لغو سفارش"
              tone="outline"
              loading={cancel.isPending}
              onPress={() => cancel.mutate(o.number, { onError: (e) => setError(e.message) })}
            />
          </View>
        )}
      </Page>
    </View>
  );
}
