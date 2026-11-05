import { router } from 'expo-router';
import { RefreshControl, ScrollView, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Arch } from '@/components/Arch';
import { BannerCarousel, CategoryTiles, ProductGrid } from '@/components/home';
import { ErrorState, IconButton, Loading, SectionHeader, T } from '@/components/ui';
import { DEMO } from '@/lib/demo/runtime';
import { useHome, useQuota } from '@/lib/queries';
import { colors, GUTTER, space } from '@/theme/tokens';

/**
 * Home, in the order the client asked for:
 * 1. three top slides, 2. clothing categories with photos, 3. ad slides,
 * then the newest items.
 */
export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const home = useHome();
  const quota = useQuota();

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.porcelain }}
      contentContainerStyle={{ paddingTop: insets.top + space.md, paddingBottom: space.xxxl, gap: space.xl }}
      refreshControl={
        <RefreshControl
          refreshing={home.isRefetching}
          onRefresh={() => {
            home.refetch();
            quota.refetch();
          }}
          tintColor={colors.anar}
        />
      }
    >
      {DEMO && (
        <View style={{ marginHorizontal: GUTTER, backgroundColor: colors.ink, borderRadius: 999, paddingVertical: 6, paddingHorizontal: space.lg }}>
          <T variant="tiny" color="#FFFFFF" center>
            نسخه‌ی نمایشی: محصولات نمونه‌اند و پرداخت واقعی انجام نمی‌شود
          </T>
        </View>
      )}

      <View style={{ paddingHorizontal: GUTTER, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: space.sm }}>
          <Arch width={18} height={34} bottomRadius={0} background={colors.anar} style={{ marginBottom: 14 }} />
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
          <BannerCarousel banners={home.data.banners_top.slice(0, 3)} width={width} />

          {home.data.categories.length > 0 && (
            <View>
              <SectionHeader title="دسته‌بندی پوشاک" />
              <CategoryTiles categories={home.data.categories} width={width} columns={3} />
            </View>
          )}

          {home.data.banners_middle.length > 0 && (
            <BannerCarousel banners={home.data.banners_middle.slice(0, 3)} width={width} interval={5500} />
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
