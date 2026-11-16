import { NextResponse } from 'next/server';

/**
 * Hides the design-only screens in production until staff sign-in exists (ADR-007, ADR-008).
 *
 * The sign-in screens only mirror the supplied designs: their form would put a typed password
 * in the URL, so they must not be reachable on the public site. The developer screen index at
 * "/" is hidden too, and "/" opens the overview instead. Set IHUB_SHOW_PREVIEWS=true (the
 * default for `npm run dev`) to see every screen.
 */
const DESIGN_ONLY_PATHS = [
  '/login',
  '/forgot-password',
  '/create-password',
  '/verify-code',
  '/accept-invitation',
  '/choose-workspace',
];

function previewsShown() {
  const flag = process.env.IHUB_SHOW_PREVIEWS;
  if (flag !== undefined) return flag === 'true';
  return process.env.NODE_ENV !== 'production';
}

function isDesignOnly(pathname) {
  return DESIGN_ONLY_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

export function proxy(request) {
  if (previewsShown()) return undefined;

  const { pathname } = request.nextUrl;
  if (pathname === '/' || isDesignOnly(pathname)) {
    return NextResponse.redirect(new URL('/overview', request.url));
  }
  return undefined;
}

export const config = {
  matcher: [
    '/',
    '/login/:path*',
    '/forgot-password/:path*',
    '/create-password/:path*',
    '/verify-code/:path*',
    '/accept-invitation/:path*',
    '/choose-workspace/:path*',
  ],
};
