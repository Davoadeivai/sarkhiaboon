import { router } from 'expo-router';
import { FlatList, useWindowDimensions, View } from 'react-native';

import { ProductCard } from '@/components/ProductCard';
import { ScreenHeader } from '@/components/Screen';
import { EmptyState, ErrorState, Loading } from '@/components/ui';
import { useFavorites } from '@/lib/queries';
import { colors, GUTTER, space } from '@/theme/tokens';

export default function FavoritesScreen() {
  const { width } = useWindowDimensions();
  const favs = useFavorites();
  const cardW = Math.floor((width - GUTTER * 2 - space.md) / 2);
  const items = favs.data?.results.map((f) => f.product) ?? [];

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader title="علاقه‌مندی‌ها" />
      <FlatList
        data={items}
        keyExtractor={(p) => String(p.id)}
        numColumns={2}
        columnWrapperStyle={{ gap: space.md, marginBottom: space.xl }}
        contentContainerStyle={{ paddingHorizontal: GUTTER, paddingBottom: space.xxl }}
        renderItem={({ item }) => <ProductCard product={item} width={cardW} />}
        ListEmptyComponent={
          favs.isLoading ? (
            <Loading />
          ) : favs.error ? (
            <ErrorState message={favs.error.message} onRetry={() => favs.refetch()} />
          ) : (
            <EmptyState icon="heart" title="هنوز چیزی نشان نکرده‌ای" body="روی قلب هر لباس بزن تا اینجا بماند." action="رفتن به ویترین" onAction={() => router.replace('/')} />
          )
        }
      />
    </View>
  );
}
