import { useLocalSearchParams } from 'expo-router';
import { ActivityIndicator, FlatList, useWindowDimensions, View } from 'react-native';

import { BannerCarousel, CategoryTiles } from '@/components/home';
import { ProductCard } from '@/components/ProductCard';
import { ScreenHeader } from '@/components/Screen';
import { EmptyState, ErrorState, Loading, T } from '@/components/ui';
import { faDigits } from '@/lib/format';
import { useCategoryPage, useProducts } from '@/lib/queries';
import { colors, GUTTER, space } from '@/theme/tokens';

/**
 * A category page. With subcategories (مانتو → مدرسه، اداری، مجلسی، راحتی) it shows
 * the slider and the subcategory photos; a subcategory (مانتو اداری) shows the
 * slider and then its products.
 */
export default function CategoryScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const { width } = useWindowDimensions();
  const page = useCategoryPage(slug);
  const isLeaf = page.data ? page.data.children.length === 0 : false;
  const products = useProducts({ category: slug, ordering: '-created_at' });
  const cardW = Math.floor((width - GUTTER * 2 - space.md) / 2);

  if (page.isLoading) return <Loading />;
  if (page.error || !page.data)
    return (
      <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
        <ScreenHeader title="دسته‌بندی" />
        <ErrorState message={page.error?.message ?? 'این دسته پیدا نشد.'} onRetry={() => page.refetch()} />
      </View>
    );

  const c = page.data;
  const items = isLeaf ? products.data?.pages.flatMap((p) => p.results) ?? [] : [];
  const total = products.data?.pages[0]?.count ?? 0;

  const header = (
    <View style={{ gap: space.xl, paddingBottom: space.lg, marginHorizontal: -GUTTER }}>
      {c.banners.length > 0 && <BannerCarousel banners={c.banners.slice(0, 3)} width={width} />}
      {!isLeaf ? (
        <View style={{ gap: space.md }}>
          <T variant="heading" style={{ paddingHorizontal: GUTTER }}>
            {`انواع ${c.name}`}
          </T>
          <CategoryTiles categories={c.children} width={width} columns={2} />
        </View>
      ) : (
        products.isSuccess && (
          <T variant="small" color={colors.mute} style={{ paddingHorizontal: GUTTER }}>
            {total ? `${faDigits(total)} مدل از فروشگاه‌های ثبت‌شده` : ''}
          </T>
        )
      )}
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader title={c.name} />
      <FlatList
        data={items}
        keyExtractor={(p) => String(p.id)}
        numColumns={2}
        ListHeaderComponent={header}
        contentContainerStyle={{ paddingHorizontal: GUTTER, paddingBottom: space.xxxl }}
        columnWrapperStyle={{ gap: space.md, marginBottom: space.xl }}
        renderItem={({ item }) => <ProductCard product={item} width={cardW} />}
        onEndReached={() => isLeaf && products.hasNextPage && !products.isFetchingNextPage && products.fetchNextPage()}
        onEndReachedThreshold={0.6}
        ListEmptyComponent={
          !isLeaf ? undefined : products.isLoading ? (
            <Loading />
          ) : products.error ? (
            <ErrorState message={products.error.message} onRetry={() => products.refetch()} />
          ) : (
            <EmptyState icon="grid" title="فعلاً مدلی در این دسته نیست" body="به‌زودی فروشگاه‌ها مدل‌های تازه اضافه می‌کنند." />
          )
        }
        ListFooterComponent={products.isFetchingNextPage ? <ActivityIndicator color={colors.firouzeh} /> : undefined}
      />
    </View>
  );
}
