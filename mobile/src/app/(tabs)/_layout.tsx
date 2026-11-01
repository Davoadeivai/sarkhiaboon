import { type BottomTabBarProps, Tabs } from 'expo-router/js-tabs';
import { Pressable, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon, type IconName } from '@/components/Icon';
import { T } from '@/components/ui';
import { faDigits } from '@/lib/format';
import { useCart } from '@/lib/queries';
import { colors, space } from '@/theme/tokens';

const TABS: { name: string; title: string; icon: IconName }[] = [
  { name: 'index', title: 'ویترین', icon: 'home' },
  { name: 'catalog', title: 'دسته‌ها', icon: 'grid' },
  { name: 'closet', title: 'کمد', icon: 'closet' },
  { name: 'cart', title: 'سبد', icon: 'bag' },
  { name: 'profile', title: 'من', icon: 'user' },
];

function TabBar({ state, emitter, navigateToTab }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  const { data: cart } = useCart();
  const count = cart?.items.reduce((n, i) => n + i.quantity, 0) ?? 0;

  return (
    <View
      accessibilityRole="tablist"
      style={{
        flexDirection: 'row',
        backgroundColor: colors.surface,
        borderTopWidth: 1,
        borderTopColor: colors.line,
        paddingBottom: Math.max(insets.bottom, space.sm),
        paddingTop: space.sm,
      }}
    >
      {state.routes.map((route, i) => {
        const tab = TABS.find((t) => t.name === route.name);
        if (!tab) return null;
        const focused = state.index === i;
        const color = focused ? colors.ink : colors.faint;
        return (
          <Pressable
            key={route.key}
            accessibilityRole="tab"
            accessibilityState={{ selected: focused }}
            accessibilityLabel={tab.name === 'cart' && count ? `${tab.title}، ${faDigits(count)} کالا` : tab.title}
            onPress={() => {
              const e = emitter.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
              if (!focused && !e.defaultPrevented) navigateToTab(route.key);
            }}
            style={{ flex: 1, alignItems: 'center', gap: 2, paddingVertical: 2 }}
          >
            <View>
              <Icon name={tab.icon} color={color} strokeWidth={focused ? 2.1 : 1.75} />
              {tab.name === 'cart' && count > 0 && (
                <View
                  style={{
                    position: 'absolute',
                    top: -4,
                    end: -10,
                    minWidth: 18,
                    height: 18,
                    borderRadius: 9,
                    paddingHorizontal: 4,
                    backgroundColor: colors.firouzeh,
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <T variant="tiny" color="#FFFFFF" style={{ lineHeight: 16 }}>
                    {faDigits(count)}
                  </T>
                </View>
              )}
            </View>
            <T variant="tiny" color={color}>
              {tab.title}
            </T>
            <View style={{ width: 16, height: 3, borderRadius: 2, backgroundColor: focused ? colors.firouzeh : 'transparent' }} />
          </Pressable>
        );
      })}
    </View>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{ headerShown: false, sceneStyle: { backgroundColor: colors.porcelain } }}
      tabBar={(props) => <TabBar {...props} />}
    >
      {TABS.map((t) => (
        <Tabs.Screen key={t.name} name={t.name} options={{ title: t.title }} />
      ))}
    </Tabs>
  );
}
