/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // A self-contained server in .next/standalone, copied into the image by web/Dockerfile.
  output: 'standalone',
};

export default nextConfig;
