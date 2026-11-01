import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';

import { Arch } from '@/components/Arch';
import { Icon, type IconName } from '@/components/Icon';
import { BottomBar, ScreenHeader } from '@/components/Screen';
import { Button, Card, Loading, Notice, T } from '@/components/ui';
import { isGuest, useAuth } from '@/lib/auth';
import { faDigits } from '@/lib/format';
import { photoForm, pickImage, type PickedImage } from '@/lib/media';
import { useCreateJob, usePhotos, useProduct, useQuota, useUploadPhoto } from '@/lib/queries';
import { colors, GUTTER, space } from '@/theme/tokens';

const TIPS: { icon: IconName; title: string; body: string }[] = [
  { icon: 'person', title: 'رو به دوربین بایست', body: 'تمام‌قد یا دست‌کم تا زانو، دست‌ها کمی دور از بدن.' },
  { icon: 'sun', title: 'نور کافی', body: 'کنار پنجره یا زیر نور یکنواخت؛ بدون سایه‌ی تند.' },
  { icon: 'wall', title: 'پس‌زمینه‌ی ساده', body: 'دیوار ساده بهترین نتیجه را می‌دهد.' },
];

type Selected = { kind: 'new'; image: PickedImage } | { kind: 'saved'; id: string; uri: string };

export default function TryOnStart() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const product = useProduct(slug);
  const quota = useQuota();
  const photos = usePhotos();
  const upload = useUploadPhoto();
  const createJob = useCreateJob();
  const user = useAuth((s) => s.user);

  const [selected, setSelected] = useState<Selected | null>(null);
  const [error, setError] = useState<string | null>(null);

  const choose = async (source: 'camera' | 'library') => {
    setError(null);
    const res = await pickImage(source);
    if (!res) return;
    if ('denied' in res) {
      setError('برای گرفتن عکس، دسترسی دوربین را از تنظیمات گوشی فعال کن یا عکس را از گالری انتخاب کن.');
      return;
    }
    setSelected({ kind: 'new', image: res });
  };

  const busy = upload.isPending || createJob.isPending;
  const noQuota = quota.data ? quota.data.remaining <= 0 : false;

  const start = async () => {
    if (!selected || !product.data) return;
    setError(null);
    try {
      let photoId: string;
      let preview: string;
      if (selected.kind === 'new') {
        const photo = await upload.mutateAsync(await photoForm(selected.image));
        photoId = photo.id;
        preview = selected.image.uri;
      } else {
        photoId = selected.id;
        preview = selected.uri;
      }
      const job = await createJob.mutateAsync({ productId: product.data.id, photoId });
      router.replace({ pathname: '/tryon/job/[id]', params: { id: job.id, preview } });
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (product.isLoading) return <Loading />;
  const p = product.data;
  const recent = (photos.data ?? []).slice(0, 6);
  const previewUri = selected?.kind === 'new' ? selected.image.uri : selected?.uri;

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader title="پرو مجازی" />
      <ScrollView contentContainerStyle={{ paddingHorizontal: GUTTER, paddingBottom: space.xxl, gap: space.xl }}>
        {p && (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
            <Arch width={56} height={72}>
              {p.image && <Image source={{ uri: p.image }} style={{ width: 56, height: 72 }} contentFit="cover" />}
            </Arch>
            <View style={{ flex: 1 }}>
              <T variant="small" color={colors.mute}>
                لباسی که پرو می‌کنی
              </T>
              <T variant="bodyStrong" numberOfLines={2}>
                {p.name}
              </T>
            </View>
          </View>
        )}

        <View style={{ gap: space.sm }}>
          <T variant="title" accessibilityRole="header">
            یک عکس از خودت
          </T>
          <T color={colors.mute}>هرچه عکس بهتر باشد، لباس طبیعی‌تر روی تنت می‌نشیند.</T>
        </View>

        {previewUri ? (
          <View style={{ alignItems: 'center', gap: space.md }}>
            <Arch width={200} height={270}>
              <Image source={{ uri: previewUri }} style={{ width: 200, height: 270 }} contentFit="cover" accessibilityLabel="عکس انتخاب‌شده" />
            </Arch>
            <Button label="عوض کردن عکس" tone="ghost" icon="refresh" onPress={() => setSelected(null)} />
          </View>
        ) : (
          <>
            <Card style={{ gap: space.lg }}>
              {TIPS.map((tip) => (
                <View key={tip.title} style={{ flexDirection: 'row', gap: space.md, alignItems: 'flex-start' }}>
                  <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: colors.firouzehMist, alignItems: 'center', justifyContent: 'center' }}>
                    <Icon name={tip.icon} size={22} color={colors.firouzeh} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <T variant="bodyStrong">{tip.title}</T>
                    <T variant="small" color={colors.mute}>
                      {tip.body}
                    </T>
                  </View>
                </View>
              ))}
            </Card>

            <View style={{ flexDirection: 'row', gap: space.md }}>
              <Button label="عکس بگیر" icon="camera" tone="ink" style={{ flex: 1 }} onPress={() => choose('camera')} />
              <Button label="از گالری" icon="image" tone="outline" style={{ flex: 1 }} onPress={() => choose('library')} />
            </View>

            {recent.length > 0 && (
              <View style={{ gap: space.sm }}>
                <T variant="bodyStrong">عکس‌های اخیرت</T>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }}>
                  {recent.map((ph) => (
                    <Pressable
                      key={ph.id}
                      accessibilityRole="button"
                      accessibilityLabel="استفاده از این عکس"
                      onPress={() => setSelected({ kind: 'saved', id: ph.id, uri: ph.image })}
                    >
                      <Arch width={64} height={86}>
                        <Image source={{ uri: ph.image }} style={{ width: 64, height: 86 }} contentFit="cover" />
                      </Arch>
                    </Pressable>
                  ))}
                </ScrollView>
              </View>
            )}
          </>
        )}

        <View style={{ flexDirection: 'row', gap: space.sm, alignItems: 'flex-start' }}>
          <Icon name="lock" size={18} color={colors.mute} />
          <T variant="small" color={colors.mute} style={{ flex: 1 }}>
            عکست فقط برای ساخت همین تصویر استفاده می‌شود، اطلاعات مکانش پاک می‌شود و حداکثر ۲۴ ساعت بعد خودکار حذف می‌شود.
          </T>
        </View>

        {noQuota && (
          <Notice
            tone="warn"
            text={
              isGuest(user)
                ? 'سهمیه‌ی پروی امروزت تمام شد. با ورود با شماره موبایل، سهمیه‌ی روزانه‌ات بیشتر می‌شود.'
                : 'سهمیه‌ی پروی امروزت تمام شد. فردا دوباره می‌توانی پرو کنی.'
            }
          />
        )}
        {error && <Notice tone="error" text={error} />}
      </ScrollView>

      <BottomBar>
        {noQuota && isGuest(user) ? (
          <Button label="ورود با شماره موبایل" size="lg" style={{ flex: 1 }} onPress={() => router.push('/login')} />
        ) : (
          <View style={{ flex: 1, gap: space.xs }}>
            <Button label="پرو کن" icon="arch" size="lg" disabled={!selected || noQuota} loading={busy} onPress={start} />
            {quota.data && (
              <T variant="tiny" color={colors.mute} center>
                {`${faDigits(quota.data.remaining)} از ${faDigits(quota.data.limit)} پروی امروز باقی مانده`}
              </T>
            )}
          </View>
        )}
      </BottomBar>
    </View>
  );
}

