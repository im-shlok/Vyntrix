'use client';

import { useEffect } from 'react';

/**
 * Remove data written by the old browser-only auth/community implementation.
 * Current identity, profiles, and posts are server-owned and never use these
 * keys. This is intentionally limited to Agriva's legacy keys.
 */
export default function LegacyStorageCleanup() {
  useEffect(() => {
    window.localStorage.removeItem('kisaan_session');
    window.localStorage.removeItem('kisaan_community_chats');

    for (let index = window.localStorage.length - 1; index >= 0; index -= 1) {
      const key = window.localStorage.key(index);
      if (key?.startsWith('kisaan_user_')) {
        window.localStorage.removeItem(key);
      }
    }
  }, []);

  return null;
}
