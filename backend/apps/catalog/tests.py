from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.signals import guest_merged
from apps.core.testing import APITestBase, make_image

from .models import Banner, Category, Favorite, HomeShortcut, ProductVariant, TryOnType
from .testing import make_category, make_product


class ModelTests(APITestBase):
    def test_persian_slug_is_generated_and_unique(self):
        a = make_category(name="لباس زنانه")
        b = make_category(name="لباس زنانه")
        self.assertEqual(a.slug, "لباس-زنانه")
        self.assertEqual(b.slug, "لباس-زنانه-2")

    def test_tryon_type_inherited_from_category(self):
        cat = make_category(tryon_type=TryOnType.LOWER_BODY)
        product = make_product(category=cat)
        self.assertEqual(product.effective_tryon_type, TryOnType.LOWER_BODY)
        product.tryon_type = TryOnType.DRESSES
        self.assertEqual(product.effective_tryon_type, TryOnType.DRESSES)

    def test_supports_tryon(self):
        self.assertTrue(make_product().supports_tryon)
        self.assertFalse(make_product(name="کیف", category=make_category("کیف", TryOnType.NONE)).supports_tryon)
        self.assertFalse(make_product(name="بلوز", tryon_enabled=False).supports_tryon)

    def test_discount_validation_and_percent(self):
        product = make_product(price=300_000, compare_at_price=400_000)
        self.assertEqual(product.discount_percent, 25)
        product.compare_at_price = 200_000
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_category_loop_is_rejected(self):
        parent = make_category("والد")
        child = make_category("فرزند", parent=parent)
        parent.parent = child
        with self.assertRaises(ValidationError):
            parent.full_clean()

    def test_banner_link_validation(self):
        banner = Banner(title="حراج", image=make_image(), link_type=Banner.LinkType.PRODUCT)
        with self.assertRaises(ValidationError):
            banner.full_clean()


class ProductAPITests(APITestBase):
    def setUp(self):
        super().setUp()
        self.women = make_category("زنانه", TryOnType.NONE)
        self.tops = make_category("بلوز", TryOnType.UPPER_BODY, parent=self.women)
        self.pants = make_category("شلوار", TryOnType.LOWER_BODY)
        self.blouse = make_product("بلوز حریر", category=self.tops, price=500_000, sizes=("S", "M"))
        self.jeans = make_product("شلوار جین", category=self.pants, price=900_000, compare_at_price=1_200_000, stock=0)

    def test_list_is_public(self):
        resp = self.client.get("/api/v1/catalog/products/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)

    def test_expired_token_still_browses(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer expired-or-garbage")
        self.assertEqual(self.client.get("/api/v1/catalog/products/").status_code, 200)

    def test_inactive_products_hidden(self):
        self.jeans.is_active = False
        self.jeans.save()
        self.assertEqual(self.client.get("/api/v1/catalog/products/").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/v1/catalog/products/{self.jeans.slug}/").status_code, 404)

    def test_category_filter_includes_subcategories(self):
        resp = self.client.get("/api/v1/catalog/products/", {"category": self.women.slug})
        self.assertEqual([p["name"] for p in resp.data["results"]], ["بلوز حریر"])

    def test_price_size_stock_filters(self):
        get = lambda **q: [p["name"] for p in self.client.get("/api/v1/catalog/products/", q).data["results"]]
        self.assertEqual(get(max_price=600_000), ["بلوز حریر"])
        self.assertEqual(get(size="s"), ["بلوز حریر"])
        self.assertEqual(get(in_stock="true"), ["بلوز حریر"])
        self.assertEqual(get(discounted="true"), ["شلوار جین"])

    def test_tryon_filter(self):
        make_product("کیف دستی", category=make_category("کیف", TryOnType.NONE))
        names = {p["name"] for p in self.client.get("/api/v1/catalog/products/", {"tryon": "true"}).data["results"]}
        self.assertEqual(names, {"بلوز حریر", "شلوار جین"})

    def test_shoes_not_offered_for_tryon_while_engine_cannot_do_them(self):
        """Regression: found in the live end-to-end run — the home screen offered shoes for try-on."""
        shoes = make_product("کتانی", category=make_category("کفش", TryOnType.SHOES))
        names = {p["name"] for p in self.client.get("/api/v1/catalog/products/", {"tryon": "true"}).data["results"]}
        self.assertNotIn("کتانی", names)
        detail = self.client.get(f"/api/v1/catalog/products/{shoes.slug}/").data
        self.assertFalse(detail["supports_tryon"])
        home = self.client.get("/api/v1/catalog/home/").data
        self.assertNotIn("کتانی", {p["name"] for p in home["tryon_products"]})

    def test_search_and_ordering(self):
        resp = self.client.get("/api/v1/catalog/products/", {"search": "جین"})
        self.assertEqual(resp.data["count"], 1)
        resp = self.client.get("/api/v1/catalog/products/", {"ordering": "price"})
        self.assertEqual([p["price"] for p in resp.data["results"]], [500_000, 900_000])

    def test_detail_has_variants_images_and_full_urls(self):
        resp = self.client.get(f"/api/v1/catalog/products/{self.blouse.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["variants"]), 2)
        self.assertEqual(resp.data["tryon_type"], "upper_body")
        self.assertTrue(resp.data["image"].startswith("http://"))
        self.assertTrue(resp.data["in_stock"])

    def test_out_of_stock_flag(self):
        resp = self.client.get(f"/api/v1/catalog/products/{self.jeans.slug}/")
        self.assertFalse(resp.data["in_stock"])
        self.assertEqual(resp.data["discount_percent"], 25)

    def test_category_tree(self):
        resp = self.client.get("/api/v1/catalog/categories/")
        women = next(c for c in resp.data if c["slug"] == self.women.slug)
        self.assertEqual([c["name"] for c in women["children"]], ["بلوز"])


class HomeAndBannerTests(APITestBase):
    def setUp(self):
        super().setUp()
        self.product = make_product()
        now = timezone.now()
        Banner.objects.create(title="تابستانه", image=make_image(), position=Banner.Position.HOME_TOP,
                              link_type=Banner.LinkType.PRODUCT, product=self.product)
        Banner.objects.create(title="تمام‌شده", image=make_image(), ends_at=now - timedelta(days=1))
        Banner.objects.create(title="آینده", image=make_image(), starts_at=now + timedelta(days=1))
        Banner.objects.create(title="وسط", image=make_image(), position=Banner.Position.HOME_MIDDLE,
                              link_type=Banner.LinkType.URL, url="https://example.com")
        HomeShortcut.objects.create(title="حراج", icon=make_image(), link_type=HomeShortcut.LinkType.CATEGORY,
                                    category=self.product.category)
        self.product.category.show_on_home = True
        self.product.category.icon = make_image("icon.png", (64, 64), fmt="PNG")
        self.product.category.save()

    def test_only_live_banners_are_returned(self):
        titles = {b["title"] for b in self.client.get("/api/v1/catalog/banners/").data}
        self.assertEqual(titles, {"تابستانه", "وسط"})

    def test_banner_position_filter(self):
        resp = self.client.get("/api/v1/catalog/banners/", {"position": "home_middle"})
        self.assertEqual([b["title"] for b in resp.data], ["وسط"])

    def test_home_payload(self):
        resp = self.client.get("/api/v1/catalog/home/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([b["title"] for b in resp.data["banners_top"]], ["تابستانه"])
        self.assertEqual(resp.data["banners_top"][0]["link"], {"type": "product", "slug": self.product.slug})
        self.assertEqual(resp.data["banners_middle"][0]["link"], {"type": "url", "url": "https://example.com"})
        self.assertEqual(resp.data["shortcuts"][0]["link"]["type"], "category")
        self.assertEqual(len(resp.data["categories"]), 1)
        self.assertIsNotNone(resp.data["categories"][0]["icon"])
        self.assertEqual(len(resp.data["new_products"]), 1)
        self.assertEqual(len(resp.data["tryon_products"]), 1)


class FavoriteTests(APITestBase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(phone="09121234567")
        self.product = make_product()
        self.authenticate(self.user)

    def test_add_list_remove_and_flag(self):
        resp = self.client.post("/api/v1/catalog/favorites/", {"product_id": self.product.pk}, format="json")
        self.assertEqual(resp.status_code, 201)
        again = self.client.post("/api/v1/catalog/favorites/", {"product_id": self.product.pk}, format="json")
        self.assertEqual(again.status_code, 200)  # idempotent
        self.assertEqual(Favorite.objects.count(), 1)

        listing = self.client.get("/api/v1/catalog/favorites/")
        self.assertEqual(listing.data["count"], 1)
        self.assertTrue(listing.data["results"][0]["product"]["is_favorite"])

        detail = self.client.get(f"/api/v1/catalog/products/{self.product.slug}/")
        self.assertTrue(detail.data["is_favorite"])

        self.assertEqual(self.client.delete(f"/api/v1/catalog/favorites/{self.product.pk}/").status_code, 204)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_favorites_require_login(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/catalog/favorites/").status_code, 401)

    def test_guest_favorites_move_on_merge(self):
        guest = User.objects.create_guest()
        other = make_product("شلوار")
        Favorite.objects.create(user=guest, product=self.product)
        Favorite.objects.create(user=guest, product=other)
        Favorite.objects.create(user=self.user, product=self.product)  # duplicate
        guest_merged.send(sender=User, guest=guest, user=self.user)
        self.assertEqual(Favorite.objects.filter(user=self.user).count(), 2)
        self.assertEqual(Favorite.objects.filter(user=guest).count(), 0)
