/**
 * Push notifications: "your try-on is ready", "your order was shipped".
 *
 * Permission is NOT asked at launch. It is asked at the moment it makes sense
 * (the customer starts a try-on or places an order); after that the token is
 * re-registered silently whenever the logged-in account changes, so the server
 * always sends to whoever is using this phone now.
 */
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { useEffect } from 'react';
import { Platform } from 'react-native';

import { api } from './api';
import { useAuth } from './auth';
import { demoApi } from './demo/runtime';
import { storage } from './storage';

const TOKEN_KEY = 'sk.pushToken';
const supported = Platform.OS !== 'web' && !demoApi;

if (supported) {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

function projectId(): string | undefined {
  const extra = Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined;
  return extra?.eas?.projectId || Constants.easConfig?.projectId || undefined;
}

/** Ask (if `ask`) and register this phone's token with the server. Never throws. */
export async function registerForPush(ask = false): Promise<void> {
  if (!supported || !Device.isDevice) return;
  try {
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('default', {
        name: 'اعلان‌های سرخیابون',
        importance: Notifications.AndroidImportance.DEFAULT,
      });
    }
    let { status } = await Notifications.getPermissionsAsync();
    if (status !== 'granted' && ask) status = (await Notifications.requestPermissionsAsync()).status;
    if (status !== 'granted') return;

    const id = projectId();
    if (!id) return; // EAS project not configured yet (set extra.eas.projectId in app.json)
    const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId: id });
    await api('/notifications/devices/', { method: 'POST', body: { token, platform: Platform.OS === 'ios' ? 'ios' : 'android' } });
    await storage.set(TOKEN_KEY, token);
  } catch {
    // Notifications are a convenience; the app works the same without them.
  }
}

/** Call before logging out, while the old session is still valid. */
export async function unregisterPush(): Promise<void> {
  if (!supported) return;
  const token = await storage.get(TOKEN_KEY);
  if (!token) return;
  await api('/notifications/devices/', { method: 'DELETE', body: { token } }).catch(() => {});
  await storage.remove(TOKEN_KEY);
}

type PushData = { type?: string; job_id?: string; order_number?: string };

function open(response: Notifications.NotificationResponse | null) {
  const data = (response?.notification.request.content.data ?? {}) as PushData;
  if (data.type === 'tryon' && data.job_id) router.push({ pathname: '/tryon/job/[id]', params: { id: data.job_id } });
  else if (data.type === 'order' && data.order_number) router.push({ pathname: '/orders/[number]', params: { number: data.order_number } });
}

/** Mounted once inside the navigator: keeps the token current and opens the right screen on tap. */
export function PushBridge() {
  const userId = useAuth((s) => s.user?.id);

  useEffect(() => {
    if (userId) registerForPush(false);
  }, [userId]);

  useEffect(() => {
    if (!supported) return;
    // Tapped while the app was closed
    const last = Notifications.getLastNotificationResponse();
    if (last) {
      open(last);
      Notifications.clearLastNotificationResponse();
    }
    const sub = Notifications.addNotificationResponseReceivedListener(open);
    return () => sub.remove();
  }, []);

  return null;
}
