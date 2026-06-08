import { Injectable } from '@angular/core';

export interface JWTPayload {
  userId: number;
  email: string;
  iat: number; // Issued at
  exp: number; // Expiration
}

@Injectable({
  providedIn: 'root'
})
export class JwtService {
  private readonly SECRET_KEY = 'mindful-moment-secret-key-change-in-production'; // In production, use environment variable
  private readonly TOKEN_KEY = 'mindfulMoment_token';

  /**
   * Encode JWT token (simplified version)
   */
  encode(payload: Omit<JWTPayload, 'iat' | 'exp'>, expiresInHours: number = 24): string {
    const now = Math.floor(Date.now() / 1000);
    const exp = now + (expiresInHours * 60 * 60);

    const jwtPayload: JWTPayload = {
      ...payload,
      iat: now,
      exp
    };

    // Base64 encode header and payload
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const encodedPayload = btoa(JSON.stringify(jwtPayload));
    
    // Create signature (simplified - in production use proper HMAC)
    const signature = this.createSignature(`${header}.${encodedPayload}`);
    
    return `${header}.${encodedPayload}.${signature}`;
  }

  /**
   * Decode and verify JWT token
   */
  decode(token: string): JWTPayload | null {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        return null;
      }

      const payload = JSON.parse(atob(parts[1])) as JWTPayload;
      
      // Verify signature
      const signature = this.createSignature(`${parts[0]}.${parts[1]}`);
      if (signature !== parts[2]) {
        console.error('Invalid token signature');
        return null;
      }

      // Check expiration
      const now = Math.floor(Date.now() / 1000);
      if (payload.exp < now) {
        console.error('Token expired');
        return null;
      }

      return payload;
    } catch (error) {
      console.error('Error decoding token:', error);
      return null;
    }
  }

  /**
   * Create signature (simplified - use proper HMAC in production)
   */
  private createSignature(data: string): string {
    // Simple hash function (in production, use crypto.subtle or a proper library)
    let hash = 0;
    const combined = data + this.SECRET_KEY;
    for (let i = 0; i < combined.length; i++) {
      const char = combined.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return btoa(hash.toString());
  }

  /**
   * Save token to localStorage
   */
  saveToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  /**
   * Get token from localStorage
   */
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Remove token from localStorage
   */
  removeToken(): void {
    localStorage.removeItem(this.TOKEN_KEY);
  }

  /**
   * Check if token is valid
   */
  isTokenValid(): boolean {
    const token = this.getToken();
    if (!token) return false;
    
    const payload = this.decode(token);
    return payload !== null;
  }

  /**
   * Get payload from stored token
   */
  getPayload(): JWTPayload | null {
    const token = this.getToken();
    if (!token) return null;
    return this.decode(token);
  }
}

