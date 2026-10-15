import type { User } from '../types/api';

/**
 * Derives the customer's primary display name according to AdesHub identity rules:
 * 1. Actual first and last name when available (e.g., 'Ella Jessica')
 * 2. First name if last name is missing (e.g., 'Ella')
 * 3. Username if name fields are empty
 * 4. 'My Account' fallback if no usable name or username exists
 *
 * Rule: NEVER display email addresses as the customer's primary display name.
 */
export function getUserDisplayName(user?: Partial<User> | null): string {
  if (!user) return 'My Account';

  // 1. If backend provided display_name and it is not an email address
  if (user.display_name && user.display_name.trim() && !user.display_name.includes('@')) {
    return user.display_name.trim();
  }

  // 2. Both first and last name
  const first = (user.first_name || '').trim();
  const last = (user.last_name || '').trim();
  if (first && last) {
    return `${first} ${last}`;
  }

  // 3. First name only
  if (first) {
    return first;
  }

  // 4. Fallback to username if present and not an email
  const username = (user.username || '').trim();
  if (username && !username.includes('@')) {
    return username;
  }

  // 5. Safe, clean fallback
  return 'My Account';
}

/**
 * Returns a single initial letter for avatar circles.
 * Uses the display name or first name, never the email.
 */
export function getUserAvatarInitial(user?: Partial<User> | null): string {
  const name = getUserDisplayName(user);
  return name.charAt(0).toUpperCase() || 'M';
}
