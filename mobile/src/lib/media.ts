import * as ImagePicker from 'expo-image-picker';
import { Platform } from 'react-native';

export interface PickedImage {
  uri: string;
  name: string;
  type: string;
}

// Try-on results are deliberately never written to the phone (no share/download): the client
// asked that they stay inside the app, for the shopper's trust.

/** Open the camera or the gallery. Returns null if the user cancels or denies permission. */
export async function pickImage(source: 'camera' | 'library'): Promise<PickedImage | { denied: true } | null> {
  const options: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.85, exif: false };
  let result: ImagePicker.ImagePickerResult;
  if (source === 'camera' && Platform.OS === 'web') {
    // In a phone browser this opens the camera directly (file input with "capture").
    result = await ImagePicker.launchCameraAsync(options);
  } else if (source === 'camera') {
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
