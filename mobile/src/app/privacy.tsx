import { View } from 'react-native';

import { Icon, type IconName } from '@/components/Icon';
import { Page, ScreenHeader } from '@/components/Screen';
import { T } from '@/components/ui';
import { colors, space } from '@/theme/tokens';

const POINTS: { icon: IconName; title: string; body: string }[] = [
  { icon: 'lock', title: 'فقط برای ساخت تصویر پرو', body: 'عکست برای هیچ کار دیگری استفاده نمی‌شود و در اختیار کسی قرار نمی‌گیرد.' },
  { icon: 'pin', title: 'بدون اطلاعات مکان', body: 'اطلاعات مکان و مشخصات دوربین، همان لحظه‌ی دریافت از عکس پاک می‌شود.' },
  { icon: 'trash', title: 'حذف خودکار', body: 'عکس اصلی‌ات حداکثر ۲۴ ساعت بعد به‌طور خودکار پاک می‌شود. تصاویر نتیجه تا وقتی نگهشان داری در کمدت می‌مانند.' },
  { icon: 'user', title: 'حتی مدیر فروشگاه هم نمی‌بیند', body: 'در پنل مدیریت، پیش‌نمایش عکس مشتری‌ها نمایش داده نمی‌شود.' },
];

export default function PrivacyScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: colors.porcelain }}>
      <ScreenHeader title="حریم خصوصی عکس‌ها" />
      <Page>
        {POINTS.map((p) => (
          <View key={p.title} style={{ flexDirection: 'row', gap: space.md, alignItems: 'flex-start' }}>
            <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.firouzehMist, alignItems: 'center', justifyContent: 'center' }}>
              <Icon name={p.icon} size={22} color={colors.firouzeh} />
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <T variant="bodyStrong">{p.title}</T>
              <T color={colors.mute}>{p.body}</T>
            </View>
          </View>
        ))}
      </Page>
    </View>
  );
}
