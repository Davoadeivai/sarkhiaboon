import { File, Paths } from 'expo-file-system';
import * as ImagePicker from 'expo-image-picker';
import * as Sharing from 'expo-sharing';
import { Platform } from 'react-native';

export interface PickedImage {
  uri: string;
  name: string;
  type: string;
}

/** Open the camera or the gallery. Returns null if the user cancels or denies permission. */
export async function pickImage(source: 'camera' | 'library'): Promise<PickedImage | { denied: true } | null> {
  const options: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.85, exif: false };
  let result: ImagePicker.ImagePickerResult;
  if (source === 'camera' && Platform.OS !== 'web') {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) return { denied: true };
    result = await ImagePicker.launchCameraAsync(options);
  } else {
    result = await ImagePicker.launchImageLibraryAsync(options);
  }
  if (result.canceled || !result.assets?.length) return null;
  const a = result.assets[0];
  return { uri: a.uri, name: a.fileName ?? 'photo.jpg', type: a.mimeType ?? 'image/jpeg' };
}

/** multipart/form-data body for POST /tryon/photos/ on both phones and the web. */
export async function photoForm(img: PickedImage): Promise<FormData> {
  const form = new FormData();
  if (Platform.OS === 'web') {
    const blob = await (await fetch(img.uri)).blob();
    form.append('image', blob, img.name);
  } else {
    // React Native's FormData accepts a file descriptor object.
    form.append('image', { uri: img.uri, name: img.name, type: img.type } as unknown as Blob);
  }
  return form;
}

/** Share a try-on result to WhatsApp, Telegram, Instagram… via the system share sheet. */
export async function shareImage(url: string, title: string): Promise<void> {
  if (Platform.OS === 'web') {
    const nav = globalThis.navigator as Navigator | undefined;
    if (nav?.share) {
      await nav.share({ title, url }).catch(() => {});
    } else {
      globalThis.open?.(url, '_blank');
    }
    return;
  }
  const name = url.split('/').pop()?.split('?')[0] || 'sarkhiaboon.png';
  const file = await File.downloadFileAsync(url, new File(Paths.cache, name), { idempotent: true });
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(file.uri, { mimeType: 'image/png', dialogTitle: title });
  }
}
