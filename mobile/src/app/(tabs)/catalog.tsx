import { router, useLocalSearchParams } from 'expo-router';
import { type ComponentRef, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, ScrollView, TextInput, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon } from '@/components/Icon';
import { ProductCard } from '@/components/ProductCard';
import { Chip, EmptyState, ErrorState, Loading, T } from '@/components/ui';
import { faDigits } from '@/lib/format';
import { type ProductFilters, useCategories, useProducts } from '@/lib/queries';
import { colors, fonts, GUTTER, radius, space } from '@/theme/tokens';

const SORTS: { value: NonNullable<ProductFilters['ordering']>; label: string }[] = [
  { value: '-created_at', label: 'جدیدترین' },
  { value: 'price', label: 'ارزان‌ترین' },
  { value: '-price', label: 'گران‌ترین' },
];

function useDebounced<T>(value: T, ms = 350) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

export default function CatalogScreen() {
  const params = useLocalSearchParams<{ category?: string; discounted?: string; tryon?: string; focus?: string }>();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const cardW = Math.floor((width - GUTTER * 2 - space.md) / 2);
  const searchRef = useRef<ComponentRef<typeof TextInput>>(null);

  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string | undefined>(params.category);
  const [tryon, setTryon] = useState(params.tryon === '1');
  const [discounted, setDiscounted] = useState(params.discounted === '1');
  const [inStock, setInStock] = useState(false);
  const [ordering, setOrdering] = useState<ProductFilters['ordering']>('-created_at');

  // Arriving from a banner, shortcut or "see all" link updates the filters.
  useEffect(() => {
    if (params.category !== undefined) setCategory(params.category || undefined);
    if (params.discounted !== undefined) setDiscounted(params.discounted === '1');
    if (params.tryon !== undefined) setTryon(params.tryon === '1');
    if (params.focus === '1') setTimeout(() => searchRef.current?.focus(), 300);
  }, [params.category, params.discounted, params.tryon, params.focus]);

  const debounced = useDebounced(search.trim());
  const filters = useMemo<ProductFilters>(
    () => ({ search: debounced || undefined, category, tryon, discounted, in_stock: inStock, ordering }),
    [debounced, category, tryon, discounted, inStock, ordering],
  );
  const products = useProducts(filters);
  const categories = useCategories();
  const items = products.data?.pages.flatMap((p) => p.results) ?? [];
  const total = products.data?.pages[0]?.count ?? 0;

  const header = (
    <View style={{ gap: space.md, paddingBottom: space.lg }}>
      <T variant="title" accessibilityRole="header">
        دسته‌ها
      </T>
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: space.sm,
          backgroundColor: colors.surface,
          borderRadius: radius.pill,
          borderWidth: 1.5,
          borderColor: colors.line,
          paddingHorizontal: space.lg,
          minHeight: 50,
        }}
      >
        <Icon name="search" size={20} color={colors.mute} />
        <TextInput
          ref={searchRef}
          value={search}
          onChangeText={setSearch}
          placeholder="جست‌وجوی لباس، رنگ یا دسته"
          placeholderTextColor={colors.faint}
          returnKeyType="search"
          accessibilityLabel="جست‌وجو"
          style={{ flex: 1, fontFamily: fonts.body, fontSize: 15, color: colors.ink, paddingVertical: space.md, writingDirection: 'rtl' }}
        />
        {!!search && (
          <Pressable accessibilityRole="button" accessibilityLabel="پاک کردن جست‌وجو" hitSlop={10} onPress={() => setSearch('')}>
            <Icon name="close" size={18} color={colors.mute} />
          </Pressable>
        )}
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }} style={{ marginHorizontal: -GUTTER }}>
        <View style={{ width: GUTTER - space.sm }} />
        <Chip label="همه" active={!category} onPress={() => setCategory(undefined)} />
        {(categories.data ?? []).map((c) => (
          <Chip key={c.id} label={c.name} active={category === c.slug} onPress={() => setCategory(c.slug)} />
        ))}
        <View style={{ width: GUTTER - space.sm }} />
      </ScrollView>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }} style={{ marginHorizontal: -GUTTER }}>
        <View style={{ width: GUTTER - space.sm }} />
        <Chip label="قابل پرو" active={tryon} onPress={() => setTryon((v) => !v)} />
        <Chip label="تخفیف‌دار" active={discounted} onPress={() => setDiscounted((v) => !v)} />
        <Chip label="فقط موجود" active={inStock} onPress={() => setInStock((v) => !v)} />
        <View style={{ width: 1, backgroundColor: colors.line, marginHorizontal: space.xs }} />
        {SORTS.map((s) => (
          <Chip key={s.value} label={s.label} active={ordering === s.value} onPress={() => setOrdering(s.value)} />
        ))}
        <View style={{ width: GUTTER - space.sm }} />
      </ScrollView>

      {products.isSuccess && (
        <T variant="small" color={colors.mute}>
          {total ? `${faDigits(total)} کالا` : ''}
        </T>
      )}
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <FlatList
        data={items}
        keyExtractor={(p) => String(p.id)}
        numColumns={2}
        ListHeaderComponent={header}
        contentContainerStyle={{ paddingTop: insets.top + space.md, paddingHorizontal: GUTTER, paddingBottom: space.xxxl }}
        columnWrapperStyle={{ gap: space.md, marginBottom: space.xl }}
        renderItem={({ item }) => <ProductCard product={item} width={cardW} />}
        onEndReached={() => products.hasNextPage && !products.isFetchingNextPage && products.fetchNextPage()}
        onEndReachedThreshold={0.6}
        keyboardShouldPersistTaps="handled"
        ListEmptyComponent={
          products.isLoading ? (
            <Loading />
          ) : products.error ? (
            <ErrorState message={products.error.message} onRetry={() => products.refetch()} />
          ) : (
            <EmptyState
              icon="search"
              title="چیزی پیدا نشد"
              body="فیلترها را کمتر کن یا عبارت دیگری جست‌وجو کن."
              action="پاک کردن فیلترها"
              onAction={() => {
                setSearch('');
                setCategory(undefined);
                setTryon(false);
                setDiscounted(false);
                setInStock(false);
                router.setParams({ category: '', discounted: '', tryon: '' });
              }}
            />
          )
        }
        ListFooterComponent={products.isFetchingNextPage ? <ActivityIndicator color={colors.firouzeh} /> : undefined}
      />
    </View>
  );
}
