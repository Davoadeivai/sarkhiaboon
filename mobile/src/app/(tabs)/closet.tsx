import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useState } from 'react';
import { FlatList, Pressable, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Arch } from '@/components/Arch';
import { Chip, EmptyState, ErrorState, Loading, T } from '@/components/ui';
import { faDigits } from '@/lib/format';
import { useCloset, useQuota } from '@/lib/queries';
import type { TryOnJob } from '@/lib/types';
import { colors, GUTTER, radius, space } from '@/theme/tokens';

const STATUS: Record<string, string> = { queued: 'در صف', processing: 'در حال ساخت', failed: 'ناموفق' };

export default function ClosetScreen() {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const [savedOnly, setSavedOnly] = useState(true);
  const closet = useCloset(savedOnly);
  const quota = useQuota();
  const cardW = Math.floor((width - GUTTER * 2 - space.md) / 2);
  const cardH = Math.round(cardW * 1.38);
  const items = closet.data?.results ?? [];

  const renderItem = ({ item }: { item: TryOnJob }) => (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`پرو ${item.product.name}`}
      onPress={() => router.push({ pathname: '/tryon/job/[id]', params: { id: item.id } })}
      style={{ width: cardW, gap: space.xs }}
    >
      <Arch width={cardW} height={cardH} background={colors.line}>
        {item.result_image ? (
          <Image source={{ uri: item.result_image }} style={{ width: cardW, height: cardH }} contentFit="cover" cachePolicy="memory" transition={200} />
        ) : (
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
            <T variant="smallStrong" color={colors.mute}>
              {STATUS[item.status] ?? ''}
            </T>
          </View>
        )}
      </Arch>
      <T variant="small" numberOfLines={1}>
        {item.product.name}
      </T>
    </Pressable>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <FlatList
        data={items}
        keyExtractor={(j) => j.id}
        numColumns={2}
        columnWrapperStyle={{ gap: space.md, marginBottom: space.lg }}
        contentContainerStyle={{ paddingTop: insets.top + space.md, paddingHorizontal: GUTTER, paddingBottom: space.xxxl }}
        refreshing={closet.isRefetching}
        onRefresh={() => {
          closet.refetch();
          quota.refetch();
        }}
        ListHeaderComponent={
          <View style={{ gap: space.lg, marginBottom: space.lg }}>
            <View style={{ gap: 2 }}>
              <T variant="title" accessibilityRole="header">
                کمد من
              </T>
              <T color={colors.mute}>پروهایی که نگه داشتی، کنار هم برای مقایسه.</T>
            </View>
            {quota.data && (
              <View
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  backgroundColor: colors.ink,
                  borderRadius: radius.lg,
                  paddingHorizontal: space.lg,
                  paddingVertical: space.md,
                }}
              >
                <T variant="bodyStrong" color="#FFFFFF">
                  پروی امروز
                </T>
                <View style={{ flexDirection: 'row', gap: 6 }} accessibilityLabel={`${faDigits(quota.data.remaining)} از ${faDigits(quota.data.limit)} باقی مانده`}>
                  {Array.from({ length: Math.min(quota.data.limit, 10) }).map((_, i) => (
                    <View
                      key={i}
                      style={{
                        width: 10,
                        height: 14,
                        borderTopLeftRadius: 5,
                        borderTopRightRadius: 5,
                        backgroundColor: i < quota.data!.remaining ? colors.firouzeh : 'rgba(255,255,255,0.18)',
                      }}
                    />
                  ))}
                  {quota.data.limit > 10 && (
                    <T variant="smallStrong" color="#FFFFFF" style={{ marginStart: 4 }}>
                      {`${faDigits(quota.data.remaining)}/${faDigits(quota.data.limit)}`}
                    </T>
                  )}
                </View>
              </View>
            )}
            <View style={{ flexDirection: 'row', gap: space.sm }}>
              <Chip label="نگه‌داشته‌ها" active={savedOnly} onPress={() => setSavedOnly(true)} />
              <Chip label="همه‌ی پروها" active={!savedOnly} onPress={() => setSavedOnly(false)} />
            </View>
          </View>
        }
        renderItem={renderItem}
        ListEmptyComponent={
          closet.isLoading ? (
            <Loading />
          ) : closet.error ? (
            <ErrorState message={closet.error.message} onRetry={() => closet.refetch()} />
          ) : (
            <EmptyState
              icon="closet"
              title={savedOnly ? 'کمدت هنوز خالی است' : 'هنوز چیزی پرو نکرده‌ای'}
              body={savedOnly ? 'یک لباس را پرو کن و نتیجه را با «نگه‌داشتن در کمد» اینجا بیاور.' : 'لباس‌هایی که قاب طاقی دارند را می‌توانی روی عکس خودت ببینی.'}
              action="دیدن لباس‌های قابل پرو"
              onAction={() => router.push({ pathname: '/catalog', params: { tryon: '1' } })}
            />
          )
        }
      />
    </View>
  );
}
