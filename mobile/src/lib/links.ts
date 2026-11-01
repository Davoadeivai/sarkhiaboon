import { router } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';

import type { Link } from './types';

/** Where a banner or shortcut tap goes (the server sends one normalized link object). */
export function openLink(link: Link) {
  switch (link.type) {
    case 'product':
      router.push(`/product/${link.slug}`);
      break;
    case 'category':
      router.push({ pathname: '/catalog', params: { category: link.slug } });
      break;
    case 'url':
      WebBrowser.openBrowserAsync(link.url).catch(() => {});
      break;
    default:
      break;
  }
}
