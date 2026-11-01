import { type ReactNode, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  Text,
  TextInput,
  type TextInputProps,
  type TextProps,
  type TextStyle,
  View,
  type ViewStyle,
} from 'react-native';

import { colors, fonts, GUTTER, radius, space, type } from '@/theme/tokens';
import { faNumber, toman } from '@/lib/format';
import { Icon, type IconName } from './Icon';

/* ---------------- Text ---------------- */

type Variant = keyof typeof type;

export function T({
  variant = 'body',
  color = colors.ink,
  center,
  style,
  ...rest
}: TextProps & { variant?: Variant; color?: string; center?: boolean }) {
  return (
    <Text
      {...rest}
      style={[type[variant], { color, writingDirection: 'rtl' }, center && { textAlign: 'center' }, style]}
    />
  );
}

/* ---------------- Buttons ---------------- */

type Tone = 'primary' | 'ink' | 'outline' | 'ghost';

interface ButtonProps {
  label: string;
  onPress?: () => void;
  tone?: Tone;
  icon?: IconName;
  loading?: boolean;
  disabled?: boolean;
  size?: 'md' | 'lg';
  style?: ViewStyle;
  accessibilityHint?: string;
}

const tones: Record<Tone, { bg: string; fg: string; border: string; pressed: string }> = {
  primary: { bg: colors.firouzeh, fg: '#FFFFFF', border: colors.firouzeh, pressed: colors.firouzehDeep },
  ink: { bg: colors.ink, fg: '#FFFFFF', border: colors.ink, pressed: colors.inkSoft },
  outline: { bg: colors.surface, fg: colors.ink, border: colors.line, pressed: colors.porcelain },
  ghost: { bg: 'transparent', fg: colors.firouzeh, border: 'transparent', pressed: colors.firouzehMist },
};

export function Button({ label, onPress, tone = 'primary', icon, loading, disabled, size = 'md', style, accessibilityHint }: ButtonProps) {
  const t = tones[tone];
  const inactive = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: !!inactive, busy: !!loading }}
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [
        {
          minHeight: size === 'lg' ? 56 : 46,
          paddingHorizontal: space.xl,
          borderRadius: radius.pill,
          backgroundColor: pressed ? t.pressed : t.bg,
          borderWidth: 1.5,
          borderColor: t.border,
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          gap: space.sm,
          opacity: disabled ? 0.45 : 1,
        },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={t.fg} />
      ) : (
        <>
          {icon && <Icon name={icon} size={20} color={t.fg} />}
          <T variant="bodyStrong" color={t.fg}>
            {label}
          </T>
        </>
      )}
    </Pressable>
  );
}

export function IconButton({
  name,
  onPress,
  label,
  color = colors.ink,
  filled,
  style,
}: {
  name: IconName;
  onPress?: () => void;
  label: string;
  color?: string;
  filled?: boolean;
  style?: ViewStyle;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      hitSlop={8}
      style={({ pressed }) => [
        {
          width: 44,
          height: 44,
          borderRadius: 22,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: pressed ? colors.porcelain : colors.surface,
          borderWidth: 1,
          borderColor: colors.line,
        },
        style,
      ]}
    >
      <Icon name={name} size={22} color={color} filled={filled} />
    </Pressable>
  );
}

/* ---------------- Price ---------------- */

export function Price({ price, compareAt, size = 'md' }: { price: number; compareAt?: number | null; size?: 'md' | 'lg' }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'baseline', flexWrap: 'wrap', columnGap: space.sm }}>
      <T variant={size === 'lg' ? 'heading' : 'smallStrong'}>{toman(price)}</T>
      {!!compareAt && compareAt > price && (
        <T variant="tiny" color={colors.faint} style={{ textDecorationLine: 'line-through' }}>
          {faNumber(compareAt)}
        </T>
      )}
    </View>
  );
}

export function DiscountTag({ percent }: { percent: number }) {
  if (!percent) return null;
  return (
    <View style={{ backgroundColor: colors.saffron, borderRadius: radius.pill, paddingHorizontal: 8, paddingVertical: 1 }}>
      <T variant="tiny" color={colors.ink}>{`٪${faNumber(percent)}`}</T>
    </View>
  );
}

/* ---------------- Chips ---------------- */

export function Chip({ label, active, onPress, swatch }: { label: string; active?: boolean; onPress?: () => void; swatch?: string }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: !!active }}
      onPress={onPress}
      style={{
        minHeight: 38,
        paddingHorizontal: space.lg,
        borderRadius: radius.pill,
        borderWidth: 1.5,
        borderColor: active ? colors.ink : colors.line,
        backgroundColor: active ? colors.ink : colors.surface,
        flexDirection: 'row',
        alignItems: 'center',
        gap: space.sm,
      }}
    >
      {swatch && (
        <View style={{ width: 14, height: 14, borderRadius: 7, backgroundColor: swatch, borderWidth: 1, borderColor: colors.line }} />
      )}
      <T variant="smallStrong" color={active ? '#FFFFFF' : colors.ink}>
        {label}
      </T>
    </Pressable>
  );
}

/* ---------------- Layout helpers ---------------- */

export function SectionHeader({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: GUTTER,
        marginBottom: space.md,
      }}
    >
      <T variant="heading">{title}</T>
      {action && (
        <Pressable accessibilityRole="button" onPress={onAction} hitSlop={10} style={{ flexDirection: 'row', alignItems: 'center', gap: 2 }}>
          <T variant="smallStrong" color={colors.firouzeh}>
            {action}
          </T>
          <Icon name="forward" size={16} color={colors.firouzeh} />
        </Pressable>
      )}
    </View>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return (
    <View style={[{ backgroundColor: colors.surface, borderRadius: radius.lg, padding: space.lg, borderWidth: 1, borderColor: colors.line }, style]}>
      {children}
    </View>
  );
}

export function Divider({ style }: { style?: ViewStyle }) {
  return <View style={[{ height: 1, backgroundColor: colors.line }, style]} />;
}

export function Row({ children, style, gap = space.sm }: { children: ReactNode; style?: ViewStyle; gap?: number }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center', gap }, style]}>{children}</View>;
}

/* ---------------- States ---------------- */

export function Loading({ label }: { label?: string }) {
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: space.xxl, gap: space.md }}>
      <ActivityIndicator color={colors.firouzeh} size="large" />
      {label && <T color={colors.mute}>{label}</T>}
    </View>
  );
}

export function EmptyState({
  icon,
  title,
  body,
  action,
  onAction,
}: {
  icon: IconName;
  title: string;
  body?: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <View style={{ alignItems: 'center', paddingVertical: space.xxxl, paddingHorizontal: GUTTER, gap: space.md }}>
      <View
        style={{
          width: 88,
          height: 104,
          borderTopLeftRadius: 44,
          borderTopRightRadius: 44,
          backgroundColor: colors.firouzehMist,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon name={icon} size={36} color={colors.firouzeh} />
      </View>
      <T variant="heading" center>
        {title}
      </T>
      {body && (
        <T color={colors.mute} center style={{ maxWidth: 300 }}>
          {body}
        </T>
      )}
      {action && <Button label={action} onPress={onAction} style={{ marginTop: space.sm }} />}
    </View>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View style={{ alignItems: 'center', padding: space.xxl, gap: space.md }}>
      <T color={colors.mute} center style={{ maxWidth: 320 }}>
        {message}
      </T>
      {onRetry && <Button label="تلاش دوباره" tone="outline" icon="refresh" onPress={onRetry} />}
    </View>
  );
}

export function Notice({ text, tone = 'info' }: { text: string; tone?: 'info' | 'error' | 'warn' }) {
  const bg = tone === 'error' ? colors.dangerMist : tone === 'warn' ? colors.saffronMist : colors.firouzehMist;
  const fg = tone === 'error' ? colors.danger : tone === 'warn' ? '#7A5410' : colors.firouzehDeep;
  return (
    <View accessibilityRole={tone === 'error' ? 'alert' : undefined} style={{ backgroundColor: bg, borderRadius: radius.md, padding: space.md }}>
      <T variant="small" color={fg}>
        {text}
      </T>
    </View>
  );
}

/* ---------------- Input ---------------- */

export function Field({
  label,
  error,
  hint,
  style,
  ...rest
}: TextInputProps & { label: string; error?: string; hint?: string; style?: TextStyle }) {
  const [focused, setFocused] = useState(false);
  return (
    <View style={{ gap: 6 }}>
      <T variant="smallStrong" color={colors.inkSoft}>
        {label}
      </T>
      <TextInput
        {...rest}
        accessibilityLabel={label}
        placeholderTextColor={colors.faint}
        onFocus={(e) => {
          setFocused(true);
          rest.onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          rest.onBlur?.(e);
        }}
        style={[
          {
            minHeight: 50,
            borderWidth: 1.5,
            borderColor: error ? colors.danger : focused ? colors.firouzeh : colors.line,
            borderRadius: radius.md,
            paddingHorizontal: space.lg,
            paddingVertical: space.md,
            backgroundColor: colors.surface,
            fontFamily: fonts.body,
            fontSize: 16,
            color: colors.ink,
            writingDirection: 'rtl',
          },
          // Our own turquoise border shows focus; drop the browser's default ring on web.
          Platform.OS === 'web' ? ({ outlineWidth: 0 } as TextStyle) : null,
          style,
        ]}
      />
      {error ? (
        <T variant="small" color={colors.danger}>
          {error}
        </T>
      ) : hint ? (
        <T variant="small" color={colors.mute}>
          {hint}
        </T>
      ) : null}
    </View>
  );
}
