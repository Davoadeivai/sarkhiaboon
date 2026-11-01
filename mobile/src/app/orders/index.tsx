import { router } from 'expo-router';
import { FlatList, Pressable, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { ScreenHeader } from '@/components/Screen';
import { EmptyState, ErrorState, Loading, T } from '@/components/ui';
import { faDate, faDigits, toman } from '@/lib/format';
import { useOrders } from '@/lib/queries';
import { colors, GUTTER, radius, space } from '@/theme/tokens';
import { StatusPill } from '@/components/StatusPill';

export default function OrdersScreen() {
  const orders = useOrders();
  const list = orders.data?.results ?? [];

  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader title="سفارش‌ها" />
      <FlatList
        data={list}
        keyExtractor={(o) => o.number}
        contentContainerStyle={{ paddingHorizontal: GUTTER, paddingBottom: space.xxl, gap: space.md }}
        refreshing={orders.isRefetching}
        onRefresh={() => orders.refetch()}
        renderItem={({ item }) => (
          <Pressable
            accessibilityRole="link"
            accessibilityLabel={`سفارش ${item.number}، ${item.status_label}`}
            onPress={() => router.push({ pathname: '/orders/[number]', params: { number: item.number } })}
            style={{ backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.line, padding: space.lg, gap: space.sm }}
          >
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <T variant="bodyStrong">{item.number}</T>
              <StatusPill status={item.status} label={item.status_label} />
            </View>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <T variant="small" color={colors.mute}>
                {`${faDate(item.created_at)}، ${faDigits(item.items.reduce((n, i) => n + i.quantity, 0))} کالا`}
              </T>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.xs }}>
                <T variant="smallStrong">{toman(item.total)}</T>
                <Icon name="forward" size={16} color={colors.mute} />
              </View>
            </View>
          </Pressable>
        )}
        ListEmptyComponent={
          orders.isLoading ? (
            <Loading />
          ) : orders.error ? (
            <ErrorState message={orders.error.message} onRetry={() => orders.refetch()} />
          ) : (
            <EmptyState icon="box" title="هنوز سفارشی نداری" action="رفتن به ویترین" onAction={() => router.replace('/')} />
          )
        }
      />
    </View>
  );
}
