/**
 * Offline catalog: the last home page, categories, shops and products the
 * customer saw are kept on the phone, so the store still opens (read-only)
 * when the internet drops. Personal data (try-on photos and results, closet,
 * cart, orders, addresses) is never written to disk, by design.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import type { Query } from '@tanstack/react-query';
import Constants from 'expo-constants';
import { create } from 'zustand';

export const CATALOG_CACHE_AGE = 3 * 24 * 60 * 60 * 1000; // three days

const CATALOG_KEYS = new Set(['home', 'categories', 'categoryPage', 'shop', 'banners', 'products', 'product']);

export const persister = createAsyncStoragePersister({ storage: AsyncStorage, key: 'sk.catalogCache', throttleTime: 2000 });

export const persistOptions = {
  persister,
  maxAge: CATALOG_CACHE_AGE,
  // A new app version may change the data shape: start with a fresh cache.
  buster: Constants.expoConfig?.version ?? '1',
  dehydrateOptions: {
    shouldDehydrateQuery: (query: Query) =>
      query.state.status === 'success' && CATALOG_KEYS.has(String(query.queryKey[0])),
  },
};

/** Wipe the saved catalog (logout). */
export const clearCatalogCache = () => persister.removeClient();

/** Set by the API layer: true after a request could not reach the server, false after one that did. */
export const useConnection = create<{ offline: boolean; set: (offline: boolean) => void }>((set) => ({
  offline: false,
  set: (offline) => set((s) => (s.offline === offline ? s : { offline })),
}));
