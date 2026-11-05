import { Lalezar_400Regular } from '@expo-google-fonts/lalezar';
import { Vazirmatn_400Regular, Vazirmatn_500Medium, Vazirmatn_700Bold } from '@expo-google-fonts/vazirmatn';
import { QueryClient } from '@tanstack/react-query';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { I18nManager, Platform, View } from 'react-native';

import { Intro } from '@/components/Intro';
import { OfflineBar } from '@/components/OfflineBar';
import { ErrorState } from '@/components/ui';
import { ApiError, startGuestSession } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { demoFonts } from '@/lib/demo/runtime';
import { CATALOG_CACHE_AGE, persistOptions } from '@/lib/offline';
import { PushBridge } from '@/lib/push';
import { colors } from '@/theme/tokens';

SplashScreen.preventAutoHideAsync().catch(() => {});

// The whole app is Persian and right-to-left. Native builds are forced RTL by
// the expo-localization plugin (app.json); this also covers Expo Go.
if (Platform.OS !== 'web' && !I18nManager.isRTL) {
  I18nManager.allowRTL(true);
  I18nManager.forceRTL(true);
}
if (Platform.OS === 'web' && typeof document !== 'undefined') {
  document.documentElement.dir = 'rtl';
  document.documentElement.lang = 'fa';
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      // Kept long enough for the saved offline catalog to be restored (lib/offline.ts)
      gcTime: CATALOG_CACHE_AGE,
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
    },
  },
});

export default function RootLayout() {
  const [fontsLoaded] = useFonts(demoFonts ?? { Lalezar_400Regular, Vazirmatn_400Regular, Vazirmatn_500Medium, Vazirmatn_700Bold });
  const { ready, access, hydrate } = useAuth();
  const [bootError, setBootError] = useState<string | null>(null);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  // First launch: open a guest session so the shopper can browse and try on right away.
  const startGuest = () => {
    setBootError(null);
    startGuestSession().catch((e: Error) => setBootError(e.message));
  };
  useEffect(() => {
    if (ready && !access) startGuest();
  }, [ready, access]);

  const booted = fontsLoaded && ready && (!!access || !!bootError);
  // The native splash (red, app.json) hands over to the red intro as soon as the fonts are in.
  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync().catch(() => {});
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  // One intro instance for the whole launch, so it never restarts while the app boots behind it.
  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      {booted && bootError && !access ? (
        <View style={{ flex: 1, justifyContent: 'center' }}>
          <ErrorState message={bootError} onRetry={startGuest} />
        </View>
      ) : booted ? (
        <PersistQueryClientProvider client={queryClient} persistOptions={persistOptions}>
          <StatusBar style="dark" />
          <Stack
            screenOptions={{
              headerShown: false,
              contentStyle: { backgroundColor: colors.porcelain },
            }}
          >
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="login" options={{ presentation: 'modal', animation: 'slide_from_bottom' }} />
          </Stack>
          <OfflineBar />
          <PushBridge />
        </PersistQueryClientProvider>
      ) : null}
      <Intro ready={booted} />
    </View>
  );
}
