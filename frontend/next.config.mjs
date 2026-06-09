/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config, { webpack }) => {
    // konva(react-konva→react-filerobot-image-editor 의존)의 node 빌드가 옵셔널 네이티브 모듈
    // 'canvas'를 require한다. 픽셀 에디터는 브라우저에서만 동작(RasterEditModal=next/dynamic ssr:false)
    // 하므로 'canvas'를 빈 모듈로 별칭 처리해 'Module not found: canvas' 빌드 실패를 막는다.
    config.resolve.alias = { ...(config.resolve.alias || {}), canvas: false };
    // react-filerobot-image-editor의 컴파일 산출물은 classic JSX(React.createElement)라 모듈마다
    // React를 import하지 않고 전역 React를 가정한다 → Next/webpack 번들엔 전역이 없어 모달 오픈 시
    // "ReferenceError: React is not defined"로 크래시. free 변수 React/ReactDOM을 자동 주입해 해결.
    config.plugins.push(new webpack.ProvidePlugin({ React: "react", ReactDOM: "react-dom" }));
    return config;
  },
};
export default nextConfig;
