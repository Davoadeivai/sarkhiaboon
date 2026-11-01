import { router } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { Platform } from 'react-native';

import { startPayment } from './queries';

/** Must match PAYMENT_RESULT_URL on the server (the bank sends the shopper back here). */
export const PAYMENT_RETURN_URL = 'sarkhiaboon://payment/result';

/**
 * Send the shopper to the bank and bring them back to the result screen.
 * On phones the bank opens in an in-app browser session that closes itself on
 * return; on the web preview the page simply navigates away and back.
 */
export async function payOrder(number: string): Promise<void> {
  const { payment_url } = await startPayment(number);

  if (Platform.OS === 'web') {
    globalThis.location?.assign(payment_url);
    return;
  }

  const result = await WebBrowser.openAuthSessionAsync(payment_url, PAYMENT_RETURN_URL);
  if (result.type === 'success') {
    const query = result.url.split('?')[1] ?? '';
    const params = Object.fromEntries(query.split('&').filter(Boolean).map((kv) => kv.split('=').map(decodeURIComponent)));
    router.replace({ pathname: '/payment/result', params: { order: params.order ?? number, status: params.status ?? 'failed' } });
  } else {
    // The shopper closed the bank page; the order stays reserved until it expires.
    router.replace({ pathname: '/orders/[number]', params: { number } });
  }
}
