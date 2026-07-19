const STORAGE_SALT = 'auron_suite_secure_storage_2026';

function encrypt(text: string): string {
  let result = '';
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(text.charCodeAt(i) ^ STORAGE_SALT.charCodeAt(i % STORAGE_SALT.length));
  }
  return btoa(encodeURIComponent(result));
}

function decrypt(encoded: string): string | null {
  try {
    const text = decodeURIComponent(atob(encoded));
    let result = '';
    for (let i = 0; i < text.length; i++) {
      result += String.fromCharCode(text.charCodeAt(i) ^ STORAGE_SALT.charCodeAt(i % STORAGE_SALT.length));
    }
    return result;
  } catch {
    return null;
  }
}

export function safeGetItem(key: string): string | null {
  try {
    const val = localStorage.getItem(key);
    if (val && (key === 'user' || key === 'tenant')) {
      return decrypt(val);
    }
    return val;
  } catch {
    return null;
  }
}

export function safeSetItem(key: string, value: string): void {
  try {
    let val = value;
    if (key === 'user' || key === 'tenant') {
      val = encrypt(value);
    }
    localStorage.setItem(key, val);
  } catch {
    // Storage unavailable (private browsing, quota exceeded)
  }
}

export function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // Storage unavailable
  }
}
