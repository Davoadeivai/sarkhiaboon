import { router } from 'expo-router';
import { RefreshControl, ScrollView, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Arch } from '@/components/Arch';
import { BannerCarousel, ProductGrid, ProductRail, ShortcutRow } from '@/components/home';
import { Icon } from '@/components/Icon';
import { ErrorState, IconButton, Loading, SectionHeader, T } from '@/components/ui';
import { useHome, useQuota } from '@/lib/queries';
import { faDigits } from '@/lib/format';
import { colors, GUTTER, space } from '@/theme/tokens';

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const home = useHome();
  const quota = useQuota();

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.porcelain }}
      contentContainerStyle={{ paddingTop: insets.top + space.md, paddingBottom: space.xxxl, gap: space.xl }}
      refreshControl={<RefreshControl refreshing={home.isRefetching} onRefresh={() => {
            home.refetch();
            quota.refetch();
          }} tintColor={colors.firouzeh} />}
    >
      <View style={{ paddingHorizontal: GUTTER, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: space.sm }}>
          <Arch width={18} height={34} bottomRadius={0} background={colors.firouzeh} style={{ marginBottom: 14 }} />
          <T variant="hero" accessibilityRole="header">
            سرخیابون
          </T>
        </View>
        <View style={{ flexDirection: 'row', gap: space.sm }}>
          <IconButton name="search" label="جست‌وجو" onPress={() => router.push({ pathname: '/catalog', params: { focus: '1' } })} />
          <IconButton name="heart" label="علاقه‌مندی‌ها" onPress={() => router.push('/favorites')} />
        </View>
      </View>

      {home.isLoading ? (
        <Loading />
      ) : home.error ? (
        <ErrorState message={home.error.message} onRetry={() => home.refetch()} />
      ) : home.data ? (
        <>
          <BannerCarousel banners={home.data.banners_top} width={width} />
          <ShortcutRow shortcuts={home.data.shortcuts} />

          {home.data.tryon_products.length > 0 && (
            <View style={{ gap: space.md }}>
              <View style={{ paddingHorizontal: GUTTER, gap: 2 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
                  <Icon name="arch" size={22} color={colors.firouzeh} />
                  <T variant="heading">روی عکس خودت امتحانش کن</T>
                </View>
                <T variant="small" color={colors.mute}>
                  {quota.data
                    ? `امروز ${faDigits(quota.data.remaining)} پروی رایگان داری.`
                    : 'هر لباسی که قاب طاقی دارد، قابل پرو است.'}
                </T>
              </View>
              <ProductRail products={home.data.tryon_products} cardWidth={156} />
            </View>
          )}

          <BannerCarousel banners={home.data.banners_middle} width={width} />

          {home.data.discounted_products.length > 0 && (
            <View>
              <SectionHeader
                title="تخفیف‌دارها"
                action="همه"
                onAction={() => router.push({ pathname: '/catalog', params: { discounted: '1' } })}
              />
              <ProductRail products={home.data.discounted_products} />
            </View>
          )}

          {home.data.new_products.length > 0 && (
            <View>
              <SectionHeader title="تازه رسیده" action="همه" onAction={() => router.push('/catalog')} />
              <ProductGrid products={home.data.new_products} width={width} />
            </View>
          )}
        </>
      ) : null}
    </ScrollView>
  );
}
