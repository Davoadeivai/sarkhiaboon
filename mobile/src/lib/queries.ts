import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, qs } from './api';
import { useAuth } from './auth';
import type {
  Address,
  AuthResponse,
  Cart,
  Banner,
  Category,
  CategoryPage,
  HomePayload,
  Order,
  Paginated,
  PersonPhoto,
  ProductDetail,
  ProductListItem,
  Quota,
  Shop,
  TryOnJob,
  User,
} from './types';

export const keys = {
  home: ['home'] as const,
  categories: ['categories'] as const,
  products: (f: ProductFilters) => ['products', f] as const,
  product: (slug: string) => ['product', slug] as const,
  favorites: ['favorites'] as const,
  quota: ['quota'] as const,
  photos: ['photos'] as const,
  job: (id: string) => ['job', id] as const,
  closet: ['closet'] as const,
  cart: ['cart'] as const,
  addresses: ['addresses'] as const,
  orders: ['orders'] as const,
  order: (n: string) => ['order', n] as const,
  me: ['me'] as const,
};

/* ---------------- catalog ---------------- */

export const useHome = () => useQuery({ queryKey: keys.home, queryFn: () => api<HomePayload>('/catalog/home/') });

export const useCategories = () =>
  useQuery({ queryKey: keys.categories, queryFn: () => api<Category[]>('/catalog/categories/'), staleTime: 10 * 60_000 });

export const useCategoryPage = (slug: string) =>
  useQuery({ queryKey: ['categoryPage', slug], queryFn: () => api<CategoryPage>(`/catalog/categories/${encodeURIComponent(slug)}/`) });

export const useShop = (slug: string) =>
  useQuery({ queryKey: ['shop', slug], queryFn: () => api<Shop>(`/catalog/shops/${encodeURIComponent(slug)}/`) });

/** Ad slides for one placement (e.g. tryon_wait: shown while the try-on image is being made). */
export const useBanners = (position: Banner['position']) =>
  useQuery({ queryKey: ['banners', position], queryFn: () => api<Banner[]>(`/catalog/banners/?position=${position}`), staleTime: 5 * 60_000 });

export interface ProductFilters {
  search?: string;
  category?: string;
  shop?: string;
  tryon?: boolean;
  discounted?: boolean;
  in_stock?: boolean;
  ordering?: '-created_at' | 'price' | '-price';
}

export const useProducts = (filters: ProductFilters) =>
  useInfiniteQuery({
    queryKey: keys.products(filters),
    initialPageParam: 1,
    queryFn: ({ pageParam }) => api<Paginated<ProductListItem>>(`/catalog/products/${qs({ ...filters, page: pageParam })}`),
    getNextPageParam: (last, all) => (last.next ? all.length + 1 : undefined),
  });

export const useProduct = (slug: string) =>
  useQuery({
    queryKey: keys.product(slug),
    queryFn: () => api<ProductDetail>(`/catalog/products/${encodeURIComponent(slug)}/`),
    enabled: !!slug,
  });

export const useFavorites = () =>
  useQuery({
    queryKey: keys.favorites,
    queryFn: () => api<Paginated<{ id: number; product: ProductListItem }>>('/catalog/favorites/'),
  });

export function useToggleFavorite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, on }: { productId: number; on: boolean }) =>
      on
        ? api('/catalog/favorites/', { method: 'POST', body: { product_id: productId } })
        : api(`/catalog/favorites/${productId}/`, { method: 'DELETE' }),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: keys.favorites });
      qc.invalidateQueries({ queryKey: ['product'] });
      qc.invalidateQueries({ queryKey: ['products'] });
      qc.invalidateQueries({ queryKey: keys.home });
    },
  });
}

/* ---------------- try-on ---------------- */

export const useQuota = () => useQuery({ queryKey: keys.quota, queryFn: () => api<Quota>('/tryon/quota/') });

export const usePhotos = () =>
  useQuery({ queryKey: keys.photos, queryFn: () => api<PersonPhoto[]>('/tryon/photos/') });

export function useUploadPhoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => api<PersonPhoto>('/tryon/photos/', { method: 'POST', body: form }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.photos }),
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { productId: number; photoId: string }) =>
      api<TryOnJob>('/tryon/jobs/', { method: 'POST', body: { product_id: v.productId, photo_id: v.photoId } }),
    onSuccess: (job) => {
      qc.setQueryData(keys.job(job.id), job);
      qc.invalidateQueries({ queryKey: keys.quota });
    },
  });
}

const isRunning = (job?: TryOnJob) => job?.status === 'queued' || job?.status === 'processing';

/** Polls every 1.5 s while the job waits in the queue or runs on the GPU. */
export const useJob = (id: string) =>
  useQuery({
    queryKey: keys.job(id),
    queryFn: () => api<TryOnJob>(`/tryon/jobs/${id}/`),
    refetchInterval: (q) => (isRunning(q.state.data) ? 1500 : false),
  });

export const useCloset = (savedOnly: boolean) =>
  useQuery({
    queryKey: [...keys.closet, savedOnly],
    queryFn: () => api<Paginated<TryOnJob>>(`/tryon/jobs/${savedOnly ? '?saved=true' : ''}`),
  });

export function useSaveJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, save }: { id: string; save: boolean }) =>
      api<TryOnJob>(`/tryon/jobs/${id}/save/`, { method: save ? 'POST' : 'DELETE' }),
    onSuccess: (job) => {
      qc.setQueryData(keys.job(job.id), job);
      qc.invalidateQueries({ queryKey: keys.closet });
    },
  });
}

/* ---------------- cart & orders ---------------- */

export const useCart = () => useQuery({ queryKey: keys.cart, queryFn: () => api<Cart>('/orders/cart/') });

function useCartMutation<V>(fn: (v: V) => Promise<Cart>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: (cart) => qc.setQueryData(keys.cart, cart) });
}

export const useAddToCart = () =>
  useCartMutation((v: { variantId: number; quantity?: number }) =>
    api<Cart>('/orders/cart/items/', { method: 'POST', body: { variant_id: v.variantId, quantity: v.quantity ?? 1 } }),
  );

export const useSetQuantity = () =>
  useCartMutation((v: { itemId: number; quantity: number }) =>
    api<Cart>(`/orders/cart/items/${v.itemId}/`, { method: 'PATCH', body: { quantity: v.quantity } }),
  );

export const useRemoveItem = () =>
  useCartMutation((itemId: number) => api<Cart>(`/orders/cart/items/${itemId}/`, { method: 'DELETE' }));

export const useAddresses = () =>
  useQuery({ queryKey: keys.addresses, queryFn: () => api<Address[]>('/orders/addresses/') });

export function useCreateAddress() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (a: Omit<Address, 'id'>) => api<Address>('/orders/addresses/', { method: 'POST', body: { ...a } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.addresses }),
  });
}

export function useCheckout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { addressId: number; note?: string }) =>
      api<Order>('/orders/checkout/', { method: 'POST', body: { address_id: v.addressId, note: v.note ?? '' } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.cart });
      qc.invalidateQueries({ queryKey: keys.orders });
    },
  });
}

export const startPayment = (number: string) =>
  api<{ payment_url: string }>(`/orders/${number}/pay/`, { method: 'POST' });

export const useOrders = () => useQuery({ queryKey: keys.orders, queryFn: () => api<Paginated<Order>>('/orders/') });

export const useOrder = (number: string) =>
  useQuery({ queryKey: keys.order(number), queryFn: () => api<Order>(`/orders/${number}/`) });

export function useCancelOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (number: string) => api<Order>(`/orders/${number}/cancel/`, { method: 'POST' }),
    onSuccess: (o) => {
      qc.setQueryData(keys.order(o.number), o);
      qc.invalidateQueries({ queryKey: keys.orders });
    },
  });
}

/* ---------------- account ---------------- */

export const requestOtp = (phone: string) =>
  api<{ detail: string; expires_in: number }>('/auth/otp/request/', { method: 'POST', body: { phone }, anonymous: true });

/** Sent with the guest token so the server moves the guest's cart, closet and favorites over. */
export const verifyOtp = (phone: string, code: string) =>
  api<AuthResponse>('/auth/otp/verify/', { method: 'POST', body: { phone, code } });

export function useUpdateMe() {
  const setUser = useAuth((s) => s.setUser);
  return useMutation({
    mutationFn: (v: Pick<User, 'first_name' | 'last_name'>) => api<User>('/auth/me/', { method: 'PATCH', body: { ...v } }),
    onSuccess: (u) => setUser(u),
  });
}
