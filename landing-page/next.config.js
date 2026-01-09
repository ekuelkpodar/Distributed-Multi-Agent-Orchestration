/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['images.unsplash.com', 'avatars.githubusercontent.com'],
  },
  async redirects() {
    return [
      {
        source: '/dashboard',
        destination: 'http://localhost:3001',
        permanent: false,
      },
    ];
  },
};

module.exports = nextConfig;
