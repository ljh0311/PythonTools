import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class PasswordService {
  /**
   * Hash password using SHA-256
   */
  async hashPassword(password: string): Promise<string> {
    // Use Web Crypto API for SHA-256 hashing
    const encoder = new TextEncoder();
    const data = encoder.encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return `sha256_${hashHex}`;
  }

  /**
   * Hash password synchronously (for backward compatibility)
   * Uses a simple hash but marks it differently
   */
  hashPasswordSync(password: string): string {
    // Simple hash function (fallback for sync operations)
    let hash = 0;
    for (let i = 0; i < password.length; i++) {
      const char = password.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return `mm_${Math.abs(hash).toString(16)}`;
  }

  /**
   * Verify password against hash
   * Also supports plaintext passwords for backward compatibility
   */
  async verifyPassword(password: string, storedPassword: string): Promise<boolean> {
    // If stored password is plaintext, compare directly
    if (!storedPassword.startsWith('mm_') && !storedPassword.startsWith('sha256_')) {
      return password === storedPassword;
    }
    
    // If it's SHA-256 hash, use async verification
    if (storedPassword.startsWith('sha256_')) {
      const passwordHash = await this.hashPassword(password);
      return passwordHash === storedPassword;
    }
    
    // Otherwise, use sync hash for backward compatibility
    const passwordHash = this.hashPasswordSync(password);
    return passwordHash === storedPassword;
  }

  /**
   * Check password strength
   */
  checkPasswordStrength(password: string): {
    strength: 'weak' | 'medium' | 'strong';
    score: number;
    feedback: string[];
  } {
    const feedback: string[] = [];
    let score = 0;

    if (password.length >= 8) score += 1;
    else feedback.push('Password should be at least 8 characters long');

    if (/[a-z]/.test(password)) score += 1;
    else feedback.push('Add lowercase letters');

    if (/[A-Z]/.test(password)) score += 1;
    else feedback.push('Add uppercase letters');

    if (/[0-9]/.test(password)) score += 1;
    else feedback.push('Add numbers');

    if (/[^a-zA-Z0-9]/.test(password)) score += 1;
    else feedback.push('Add special characters');

    let strength: 'weak' | 'medium' | 'strong' = 'weak';
    if (score >= 4) strength = 'strong';
    else if (score >= 2) strength = 'medium';

    return { strength, score, feedback };
  }
}

