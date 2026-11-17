/**
 * Front-end view of the RBAC table (src/ihub/auth/rbac.py). The API is the authority;
 * these helpers only decide what to show.
 */

/** True when sign-in is off (no user) or the user's role grants `permission`. */
export function can(user, permission) {
  if (!permission || !user) {
    return true;
  }
  return Array.isArray(user.permissions) && user.permissions.includes(permission);
}
