import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { BottomBar, Page, ScreenHeader } from '@/components/Screen';
import { Button, Card, Divider, Field, Loading, Notice, T } from '@/components/ui';
import type { ApiError } from '@/lib/api';
import { toman } from '@/lib/format';
import { payOrder } from '@/lib/payment';
import { useAddresses, useCart, useCheckout, useCreateAddress } from '@/lib/queries';
import { registerForPush } from '@/lib/push';
import type { Address } from '@/lib/types';
import { colors, radius, space } from '@/theme/tokens';

type Draft = Omit<Address, 'id'>;
const EMPTY: Draft = { title: 'خانه', recipient_name: '', recipient_phone: '', province: '', city: '', address: '', postal_code: '', is_default: true };

function AddressForm({ onSaved, onCancel }: { onSaved: (a: Address) => void; onCancel?: () => void }) {
  const create = useCreateAddress();
  const [d, setD] = useState<Draft>(EMPTY);
  const err = (create.error as ApiError | null)?.fields ?? {};
  const set = (k: keyof Draft) => (v: string) => setD((x) => ({ ...x, [k]: v }));

  return (
    <Card style={{ gap: space.md }}>
      <T variant="heading">نشانی تحویل</T>
      <Field label="نام گیرنده" value={d.recipient_name} onChangeText={set('recipient_name')} error={err.recipient_name} autoComplete="name" />
      <Field label="موبایل گیرنده" value={d.recipient_phone} onChangeText={set('recipient_phone')} error={err.recipient_phone} keyboardType="phone-pad" />
      <View style={{ flexDirection: 'row', gap: space.md }}>
        <View style={{ flex: 1 }}>
          <Field label="استان" value={d.province} onChangeText={set('province')} error={err.province} />
        </View>
        <View style={{ flex: 1 }}>
          <Field label="شهر" value={d.city} onChangeText={set('city')} error={err.city} />
        </View>
      </View>
      <Field label="نشانی کامل" value={d.address} onChangeText={set('address')} error={err.address} multiline style={{ minHeight: 84, textAlignVertical: 'top' }} />
      <Field label="کد پستی" value={d.postal_code} onChangeText={set('postal_code')} error={err.postal_code} keyboardType="number-pad" hint="۱۰ رقم، بدون خط تیره" />
      {create.error && !Object.keys(err).length && <Notice tone="error" text={create.error.message} />}
      <View style={{ flexDirection: 'row', gap: space.md }}>
        <Button label="ذخیره‌ی نشانی" style={{ flex: 1 }} loading={create.isPending} onPress={() => create.mutate(d, { onSuccess: onSaved })} />
        {onCancel && <Button label="انصراف" tone="outline" onPress={onCancel} />}
      </View>
    </Card>
  );
}

export default function CheckoutScreen() {
  const cart = useCart();
  const addresses = useAddresses();
  const checkout = useCheckout();
  const [selected, setSelected] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    if (selected === null && addresses.data?.length) {
      setSelected((addresses.data.find((a) => a.is_default) ?? addresses.data[0]).id);
    }
  }, [addresses.data, selected]);

  if (cart.isLoading || addresses.isLoading) return <Loading />;
  const c = cart.data;
  const list = addresses.data ?? [];
  const showForm = adding || list.length === 0;

  const submit = async () => {
    if (!selected) return;
    setError(null);
    setPaying(true);
    try {
      const order = await checkout.mutateAsync({ addressId: selected, note });
      registerForPush(true); // shipping updates
      await payOrder(order.number);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPaying(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader title="تکمیل خرید" />
      <Page>
        {list.length > 0 && (
          <View style={{ gap: space.sm }}>
            <T variant="heading">ارسال به</T>
            {list.map((a) => {
              const on = selected === a.id;
              return (
                <Pressable
                  key={a.id}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: on }}
                  onPress={() => setSelected(a.id)}
                  style={{
                    flexDirection: 'row',
                    gap: space.md,
                    padding: space.lg,
                    borderRadius: radius.lg,
                    borderWidth: 1.5,
                    borderColor: on ? colors.firouzeh : colors.line,
                    backgroundColor: colors.surface,
                  }}
                >
                  <Icon name="pin" size={22} color={on ? colors.firouzeh : colors.mute} />
                  <View style={{ flex: 1, gap: 2 }}>
                    <T variant="bodyStrong">{`${a.recipient_name} — ${a.city}`}</T>
                    <T variant="small" color={colors.mute} numberOfLines={2}>
                      {a.address}
                    </T>
                  </View>
                  <View style={{ width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: on ? colors.firouzeh : colors.line, alignItems: 'center', justifyContent: 'center' }}>
                    {on && <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colors.firouzeh }} />}
                  </View>
                </Pressable>
              );
            })}
            {!adding && <Button label="نشانی جدید" tone="ghost" icon="plus" onPress={() => setAdding(true)} />}
          </View>
        )}

        {showForm && (
          <AddressForm
            onSaved={(a) => {
              setSelected(a.id);
              setAdding(false);
            }}
            onCancel={list.length ? () => setAdding(false) : undefined}
          />
        )}

        <Field label="توضیح برای فروشنده (اختیاری)" value={note} onChangeText={setNote} maxLength={300} />

        {c && (
          <Card style={{ gap: space.sm }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <T color={colors.mute}>جمع کالاها</T>
              <T>{toman(c.subtotal)}</T>
            </View>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <T color={colors.mute}>هزینه‌ی ارسال</T>
              <T color={c.shipping_cost ? colors.ink : colors.success}>{c.shipping_cost ? toman(c.shipping_cost) : 'رایگان'}</T>
            </View>
            <Divider />
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <T variant="bodyStrong">مبلغ قابل پرداخت</T>
              <T variant="heading">{toman(c.total)}</T>
            </View>
          </Card>
        )}

        <T variant="small" color={colors.mute}>
          کالاها تا ۳۰ دقیقه برایت رزرو می‌شوند تا پرداخت را کامل کنی.
        </T>
        {error && <Notice tone="error" text={error} />}
      </Page>
      <BottomBar>
        <Button
          label={c ? `پرداخت ${toman(c.total)}` : 'پرداخت'}
          size="lg"
          style={{ flex: 1 }}
          disabled={!selected || showForm || !c?.items.length}
          loading={paying}
          onPress={submit}
        />
      </BottomBar>
    </KeyboardAvoidingView>
  );
}

