/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    let backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    
    // If Render passes raw host like 'parcelpilot-backend-p40g', append .onrender.com
    if (backendUrl && !backendUrl.includes('.') && !backendUrl.includes('localhost')) {
      backendUrl = `${backendUrl}.onrender.com`;
    }

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
