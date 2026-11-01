// Learn more: https://docs.expo.dev/guides/customizing-metro
const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Demo build (EXPO_PUBLIC_DEMO=1): swap the demo runtime stub for the in-browser
// mock server, so the real app never bundles the demo data or fonts.
const DEMO = process.env.EXPO_PUBLIC_DEMO === '1';
const runtimeStub = path.resolve(__dirname, 'src/lib/demo/runtime.ts');
const runtimeDemo = path.resolve(__dirname, 'src/lib/demo/runtime.demo.ts');
const defaultResolve = config.resolver.resolveRequest;

config.resolver.resolveRequest = (context, moduleName, platform) => {
  const resolve = defaultResolve ?? context.resolveRequest;
  const result = resolve(context, moduleName, platform);
  if (DEMO && result.type === 'sourceFile' && result.filePath === runtimeStub) {
    return { type: 'sourceFile', filePath: runtimeDemo };
  }
  return result;
};

module.exports = config;
