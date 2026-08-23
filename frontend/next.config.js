/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    let backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    
    // Ensure backendUrl starts with http:// or https://
    if (backendUrl && !backendUrl.startsWith('http://') && !backendUrl.startsWith('https://')) {
      backendUrl = `https://${backendUrl}`;
    }
    
    // Remove trailing slash if present
    backendUrl = backendUrl.replace(/\/+$/, '');

    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
