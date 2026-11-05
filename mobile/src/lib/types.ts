/** Response shapes of the Sarkhiaboon API (/api/v1). Mirrors the DRF serializers. */

export type TryOnType = 'none' | 'upper_body' | 'lower_body' | 'dresses' | 'shoes';

export interface User {
  id: number;
  phone: string | null;
  first_name: string;
  last_name: string;
  is_guest: boolean;
  date_joined: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  is_new_user: boolean;
  user: User;
}

export interface CategoryBrief {
  id: number;
  name: string;
  slug: string;
  icon: string | null;
  image: string | null;
}

export interface ShopBrief {
  id: number;
  name: string;
  slug: string;
  logo: string | null;
  city: string;
}

export interface Shop extends ShopBrief {
  cover: string | null;
  description: string;
  product_count: number;
}

export interface Category extends CategoryBrief {
  tryon_type: TryOnType;
  children: Category[];
}

export interface ProductListItem {
  id: number;
  name: string;
  slug: string;
  image: string | null;
  price: number;
  compare_at_price: number | null;
  discount_percent: number;
  category: CategoryBrief;
  shop: ShopBrief | null;
  supports_tryon: boolean;
  in_stock: boolean;
  is_favorite: boolean;
}

export interface ProductVariant {
  id: number;
  size: string;
  color: string;
  color_hex: string;
  price: number;
  in_stock: boolean;
  stock: number;
}

export interface ProductDetail extends ProductListItem {
  description: string;
  images: { id: number; image: string; alt: string }[];
  variants: ProductVariant[];
  tryon_type: TryOnType;
}

export type Link =
  | { type: 'product'; slug: string }
  | { type: 'category'; slug: string }
  | { type: 'url'; url: string }
  | { type: 'none' };

export interface Banner {
  id: number;
  title: string;
  image: string;
  position: 'home_top' | 'home_middle' | 'category_top' | 'tryon_wait';
  link: Link;
}

export interface CategoryPage extends Category {
  parent: CategoryBrief | null;
  banners: Banner[];
}

export interface Shortcut {
  id: number;
  title: string;
  icon: string;
  link: Link;
}

export interface HomePayload {
  banners_top: Banner[];
  shortcuts: Shortcut[];
  categories: Category[];
  banners_middle: Banner[];
  new_products: ProductListItem[];
  discounted_products: ProductListItem[];
  tryon_products: ProductListItem[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface PersonPhoto {
  id: string;
  image: string;
  width: number;
  height: number;
  created_at: string;
  expires_at: string;
}

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed';

export interface TryOnJob {
  id: string;
  status: JobStatus;
  status_label: string;
  queue_position: number | null;
  product: { id: number; name: string; slug: string; image: string | null; price: number };
  tryon_type: TryOnType;
  result_image: string | null;
  error_message: string;
  generation_seconds: number | null;
  from_cache: boolean;
  is_saved: boolean;
  created_at: string;
  finished_at: string | null;
}

export interface Quota {
  limit: number;
  used: number;
  remaining: number;
}

export interface CartItem {
  id: number;
  quantity: number;
  line_total: number;
  variant: {
    id: number;
    product_id: number;
    product_name: string;
    product_slug: string;
    image: string | null;
    size: string;
    color: string;
    price: number;
    stock: number;
  };
}

export interface Cart {
  items: CartItem[];
  subtotal: number;
  shipping_cost: number;
  total: number;
}

export interface Address {
  id: number;
  title: string;
  recipient_name: string;
  recipient_phone: string;
  province: string;
  city: string;
  address: string;
  postal_code: string;
  is_default: boolean;
}

export type OrderStatus = 'pending_payment' | 'paid' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'expired';

export interface Order {
  number: string;
  status: OrderStatus | string;
  status_label: string;
  items: { product_name: string; variant_label: string; unit_price: number; quantity: number; line_total: number }[];
  subtotal: number;
  shipping_cost: number;
  total: number;
  recipient_name: string;
  recipient_phone: string;
  province: string;
  city: string;
  address: string;
  postal_code: string;
  note: string;
  reserved_until: string | null;
  paid_at: string | null;
  tracking_code: string;
  created_at: string;
}
