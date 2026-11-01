import { useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { type ComponentRef, useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Arch } from '@/components/Arch';
import { Button, Field, IconButton, Notice, T } from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { DEMO } from '@/lib/demo/runtime';
import { enDigits, faDigits, faPhone } from '@/lib/format';
import { requestOtp, verifyOtp } from '@/lib/queries';
import { colors, fonts, GUTTER, radius, space } from '@/theme/tokens';

const CODE_LENGTH = 5;

export default function LoginScreen() {
  const { next } = useLocalSearchParams<{ next?: string }>();
  const insets = useSafeAreaInsets();
  const qc = useQueryClient();
  const setSession = useAuth((s) => s.setSession);

  const [step, setStep] = useState<'phone' | 'code'>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const codeRef = useRef<ComponentRef<typeof TextInput>>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [cooldown]);

  const normalized = enDigits(phone).replace(/\D/g, '');

  const send = async () => {
    setError(null);
    setBusy(true);
    try {
      await requestOtp(normalized);
      setStep('code');
      setCooldown(60);
      setTimeout(() => codeRef.current?.focus(), 250);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const verify = async (value = code) => {
    setError(null);
    setBusy(true);
    try {
      const res = await verifyOtp(normalized, enDigits(value));
      await setSession(res);
      await qc.invalidateQueries();
      if (next) router.replace(next as '/checkout');
      else router.back();
    } catch (e) {
      setError((e as Error).message);
      setCode('');
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ paddingTop: insets.top + space.md, paddingHorizontal: GUTTER, paddingBottom: space.xxl, gap: space.xl }}>
        <View style={{ flexDirection: 'row', justifyContent: 'flex-end' }}>
          <IconButton name="close" label="بستن" onPress={() => router.back()} />
        </View>

        <View style={{ alignItems: 'center', gap: space.md }}>
          <Arch width={84} height={110} background={colors.firouzeh} />
          <T variant="title" center accessibilityRole="header">
            {step === 'phone' ? 'ورود به سرخیابون' : 'کد را وارد کن'}
          </T>
          <T color={colors.mute} center style={{ maxWidth: 320 }}>
            {step === 'phone'
              ? 'با شماره موبایلت وارد شو تا سفارش ثبت کنی. هرچه تا الان در سبد و کمد داری، با تو می‌آید.'
              : `کد ${faDigits(CODE_LENGTH)} رقمی به ${faPhone(normalized)} پیامک شد.`}
          </T>
        </View>

        {step === 'phone' ? (
          <Field
            label="شماره موبایل"
            value={phone}
            onChangeText={setPhone}
            placeholder="۰۹۱۲ ۳۴۵ ۶۷۸۹"
            keyboardType="phone-pad"
            autoComplete="tel"
            textContentType="telephoneNumber"
            maxLength={14}
            onSubmitEditing={send}
            autoFocus
          />
        ) : (
          <View style={{ gap: space.sm }}>
            <TextInput
              ref={codeRef}
              value={code}
              onChangeText={(v) => {
                const digits = enDigits(v).replace(/\D/g, '').slice(0, CODE_LENGTH);
                setCode(digits);
                if (digits.length === CODE_LENGTH) verify(digits);
              }}
              keyboardType="number-pad"
              autoComplete="one-time-code"
              textContentType="oneTimeCode"
              accessibilityLabel="کد ورود"
              maxLength={CODE_LENGTH}
              style={{
                height: 64,
                borderRadius: radius.md,
                borderWidth: 1.5,
                borderColor: colors.firouzeh,
                backgroundColor: colors.surface,
                fontFamily: fonts.bold,
                fontSize: 28,
                letterSpacing: 14,
                textAlign: 'center',
                color: colors.ink,
              }}
            />
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <Button label="ویرایش شماره" tone="ghost" onPress={() => { setStep('phone'); setCode(''); setError(null); }} />
              {cooldown > 0 ? (
                <T variant="small" color={colors.mute}>{`ارسال دوباره تا ${faDigits(cooldown)} ثانیه`}</T>
              ) : (
                <Button label="ارسال دوباره" tone="ghost" onPress={send} />
              )}
            </View>
          </View>
        )}

        {DEMO && step === 'code' && <Notice text="در نسخه‌ی نمایشی پیامکی ارسال نمی‌شود؛ کد ۱۲۳۴۵ را وارد کن." />}
        {error && <Notice tone="error" text={error} />}

        <Button
          label={step === 'phone' ? 'دریافت کد' : 'ورود'}
          size="lg"
          loading={busy}
          disabled={step === 'phone' ? normalized.length < 10 : code.length !== CODE_LENGTH}
          onPress={() => (step === 'phone' ? send() : verify())}
        />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
