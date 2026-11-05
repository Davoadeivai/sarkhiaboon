import { useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Arch } from '@/components/Arch';
import { Icon, type IconName } from '@/components/Icon';
import { Button, Card, Field, Notice, T } from '@/components/ui';
import { startGuestSession } from '@/lib/api';
import { isGuest, useAuth } from '@/lib/auth';
import { faPhone } from '@/lib/format';
import { clearCatalogCache } from '@/lib/offline';
import { unregisterPush } from '@/lib/push';
import { useUpdateMe } from '@/lib/queries';
import { colors, GUTTER, radius, space } from '@/theme/tokens';

function MenuRow({ icon, label, onPress, danger }: { icon: IconName; label: string; onPress: () => void; danger?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => ({
        flexDirection: 'row',
        alignItems: 'center',
        gap: space.md,
        paddingVertical: space.md,
        paddingHorizontal: space.lg,
        backgroundColor: pressed ? colors.porcelain : colors.surface,
      })}
    >
      <Icon name={icon} size={22} color={danger ? colors.danger : colors.inkSoft} />
      <T style={{ flex: 1 }} color={danger ? colors.danger : colors.ink}>
        {label}
      </T>
      {!danger && <Icon name="forward" size={18} color={colors.faint} />}
    </Pressable>
  );
}

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const qc = useQueryClient();
  const { user, clear } = useAuth();
  const update = useUpdateMe();
  const guest = isGuest(user);

  const [first, setFirst] = useState(user?.first_name ?? '');
  const [last, setLast] = useState(user?.last_name ?? '');
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    setFirst(user?.first_name ?? '');
    setLast(user?.last_name ?? '');
  }, [user?.first_name, user?.last_name]);

  const logout = async () => {
    await unregisterPush(); // while the old session can still authenticate
    await clear();
    qc.clear();
    await clearCatalogCache();
    await startGuestSession().catch(() => {});
    router.replace('/');
  };

  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ');

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.porcelain }}
      contentContainerStyle={{ paddingTop: insets.top + space.md, paddingHorizontal: GUTTER, paddingBottom: space.xxxl, gap: space.xl }}
    >
      <T variant="title" accessibilityRole="header">
        {guest ? 'خوش آمدی' : fullName || 'حساب من'}
      </T>

      {guest ? (
        <View style={{ backgroundColor: colors.ink, borderRadius: radius.lg, padding: space.xl, gap: space.md, overflow: 'hidden' }}>
          <Arch width={120} height={160} background="rgba(255,255,255,0.06)" style={{ position: 'absolute', top: -20, start: -24 }} />
          <T variant="heading" color="#FFFFFF">
            با شماره موبایلت وارد شو
          </T>
          <T color="rgba(255,255,255,0.75)">
            برای ثبت سفارش، پیگیری ارسال و پروی روزانه‌ی بیشتر. سبد خرید و کمدت با تو می‌آید.
          </T>
          <Button label="ورود یا ثبت‌نام" onPress={() => router.push('/login')} style={{ alignSelf: 'flex-start' }} />
        </View>
      ) : (
        <Card style={{ gap: space.md }}>
          <T variant="small" color={colors.mute}>
            {faPhone(user?.phone)}
          </T>
          <View style={{ flexDirection: 'row', gap: space.md }}>
            <View style={{ flex: 1 }}>
              <Field label="نام" value={first} onChangeText={(v) => { setFirst(v); setSaved(false); }} autoComplete="given-name" />
            </View>
            <View style={{ flex: 1 }}>
              <Field label="نام خانوادگی" value={last} onChangeText={(v) => { setLast(v); setSaved(false); }} autoComplete="family-name" />
            </View>
          </View>
          {(first !== (user?.first_name ?? '') || last !== (user?.last_name ?? '')) && (
            <Button
              label="ذخیره‌ی نام"
              tone="outline"
              loading={update.isPending}
              onPress={() => update.mutate({ first_name: first.trim(), last_name: last.trim() }, { onSuccess: () => setSaved(true) })}
            />
          )}
          {saved && <Notice text="نامت ذخیره شد." />}
          {update.error && <Notice tone="error" text={update.error.message} />}
        </Card>
      )}

      <View style={{ borderRadius: radius.lg, overflow: 'hidden', borderWidth: 1, borderColor: colors.line }}>
        {!guest && <MenuRow icon="box" label="سفارش‌ها" onPress={() => router.push('/orders')} />}
        <MenuRow icon="heart" label="علاقه‌مندی‌ها" onPress={() => router.push('/favorites')} />
        <MenuRow icon="closet" label="کمد من" onPress={() => router.push('/closet')} />
        <MenuRow icon="lock" label="حریم خصوصی عکس‌ها" onPress={() => router.push('/privacy')} />
        {!guest && <MenuRow icon="logout" label="خروج از حساب" onPress={logout} danger />}
      </View>
    </ScrollView>
  );
}
