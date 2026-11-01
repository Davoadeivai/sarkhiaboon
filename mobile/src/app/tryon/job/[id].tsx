import { Image } from 'expo-image';
import * as Haptics from 'expo-haptics';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Platform, Pressable, ScrollView, useWindowDimensions, View } from 'react-native';

import { Mirror } from '@/components/Arch';
import { Icon } from '@/components/Icon';
import { BottomBar, ScreenHeader } from '@/components/Screen';
import { Button, ErrorState, Loading, Notice, Price, T } from '@/components/ui';
import { faDigits, faOrdinal } from '@/lib/format';
import { shareImage } from '@/lib/media';
import { useJob, useSaveJob } from '@/lib/queries';
import type { TryOnJob } from '@/lib/types';
import { colors, GUTTER, radius, space } from '@/theme/tokens';

function statusText(job: TryOnJob): { title: string; body: string } {
  if (job.status === 'queued') {
    const pos = job.queue_position ?? 1;
    return pos > 1
      ? { title: `نفر ${faOrdinal(pos)} در صف هستی`, body: 'به‌زودی نوبتت می‌رسد. می‌توانی همین‌جا منتظر بمانی.' }
      : { title: 'نوبت توست', body: 'پردازش تصویر همین الان شروع می‌شود.' };
  }
  return { title: 'در حال ساخت تصویر پرو', body: 'معمولاً کمتر از یک دقیقه طول می‌کشد.' };
}

export default function TryOnJobScreen() {
  const { id, preview } = useLocalSearchParams<{ id: string; preview?: string }>();
  const { width } = useWindowDimensions();
  const job = useJob(id);
  const save = useSaveJob();
  const [shareError, setShareError] = useState<string | null>(null);
  const announced = useRef(false);

  const j = job.data;
  const mirrorW = Math.min(width - GUTTER * 2, 380);

  useEffect(() => {
    if (j?.status === 'completed' && !announced.current) {
      announced.current = true;
      if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    }
  }, [j?.status]);

  if (job.isLoading) return <Loading />;
  if (job.error || !j)
    return (
      <View style={{ flex: 1 }}>
        <ScreenHeader title="پرو مجازی" />
        <ErrorState message={job.error?.message ?? 'این پرو پیدا نشد.'} onRetry={() => job.refetch()} />
      </View>
    );

  const running = j.status === 'queued' || j.status === 'processing';
  const done = j.status === 'completed';
  const failed = j.status === 'failed';

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader title={done ? 'نتیجه‌ی پرو' : 'پرو مجازی'} onBack={() => (router.canGoBack() ? router.back() : router.replace('/'))} />
      <ScrollView contentContainerStyle={{ paddingHorizontal: GUTTER, paddingBottom: space.xxl, gap: space.xl, alignItems: 'center' }}>
        <View accessibilityLiveRegion="polite" style={{ alignItems: 'center', gap: space.lg }}>
          <Mirror
            width={mirrorW}
            uri={done ? j.result_image : preview || j.product.image}
            scanning={running}
            dim={!done}
            label={done ? `تصویر پرو ${j.product.name}` : undefined}
          >
            {failed && (
              <View style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, alignItems: 'center', justifyContent: 'center' }}>
                <Icon name="close" size={40} color="#FFFFFF" />
              </View>
            )}
          </Mirror>

          {running && (
            <View style={{ alignItems: 'center', gap: 2 }}>
              <T variant="heading" center>
                {statusText(j).title}
              </T>
              <T color={colors.mute} center>
                {statusText(j).body}
              </T>
            </View>
          )}

          {done && (
            <T variant="small" color={colors.mute} center>
              {j.from_cache
                ? 'این ترکیب را قبلاً ساخته بودی؛ از سهمیه‌ات کم نشد.'
                : j.generation_seconds && j.generation_seconds >= 1
                  ? `ساخته‌شده در ${faDigits(Math.round(j.generation_seconds))} ثانیه`
                  : ''}
            </T>
          )}
        </View>

        {failed && (
          <View style={{ alignSelf: 'stretch', gap: space.md }}>
            <Notice tone="error" text={j.error_message || 'ساخت تصویر انجام نشد. با یک عکس دیگر دوباره امتحان کن.'} />
            <T variant="small" color={colors.mute}>
              پروهای ناموفق از سهمیه‌ی روزانه‌ات کم نمی‌شوند.
            </T>
          </View>
        )}

        <Pressable
          accessibilityRole="link"
          accessibilityLabel={`دیدن ${j.product.name}`}
          onPress={() => router.push(`/product/${j.product.slug}`)}
          style={{
            alignSelf: 'stretch',
            flexDirection: 'row',
            alignItems: 'center',
            gap: space.md,
            backgroundColor: colors.surface,
            borderRadius: radius.lg,
            borderWidth: 1,
            borderColor: colors.line,
            padding: space.md,
          }}
        >
          <View style={{ width: 52, height: 64, borderRadius: radius.sm, overflow: 'hidden', backgroundColor: colors.porcelain }}>
            {j.product.image && <Image source={{ uri: j.product.image }} style={{ width: 52, height: 64 }} contentFit="cover" />}
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <T variant="bodyStrong" numberOfLines={1}>
              {j.product.name}
            </T>
            <Price price={j.product.price} />
          </View>
          <Icon name="forward" size={20} color={colors.mute} />
        </Pressable>

        {done && (
          <View style={{ alignSelf: 'stretch', flexDirection: 'row', gap: space.md }}>
            <Button
              label={j.is_saved ? 'در کمد است' : 'به کمد'}
              icon={j.is_saved ? 'check' : 'closet'}
              tone="outline"
              style={{ flex: 1 }}
              loading={save.isPending}
              onPress={() => save.mutate({ id: j.id, save: !j.is_saved })}
            />
            <Button
              label="نظر دوستان"
              icon="share"
              tone="outline"
              style={{ flex: 1 }}
              onPress={() => {
                setShareError(null);
                if (j.result_image)
                  shareImage(j.result_image, `${j.product.name} — سرخیابون`).catch(() => setShareError('اشتراک‌گذاری انجام نشد.'));
              }}
            />
          </View>
        )}
        {shareError && <Notice tone="error" text={shareError} />}
      </ScrollView>

      {(done || failed) && (
        <BottomBar>
          {done ? (
            <>
              <Button label="خریدش کن" icon="bag" size="lg" style={{ flex: 1 }} onPress={() => router.push(`/product/${j.product.slug}`)} />
              <Button label="لباس دیگر" tone="outline" size="lg" style={{ flex: 1 }} onPress={() => router.push({ pathname: '/catalog', params: { tryon: '1' } })} />
            </>
          ) : (
            <Button
              label="با عکس دیگر امتحان کن"
              icon="refresh"
              size="lg"
              style={{ flex: 1 }}
              onPress={() => router.replace({ pathname: '/tryon/[slug]', params: { slug: j.product.slug } })}
            />
          )}
        </BottomBar>
      )}
    </View>
  );
}
