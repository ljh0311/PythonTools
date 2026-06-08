import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, Router, UrlTree } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable({
  providedIn: 'root'
})
export class RoleGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(route: ActivatedRouteSnapshot): boolean | UrlTree {
    if (!this.authService.isAuthenticated()) {
      return this.router.createUrlTree(['/login']);
    }
    let r: ActivatedRouteSnapshot | null = route;
    let allowedRoles: ('developer' | 'admin' | 'user')[] = [];
    while (r) {
      if (r.data['roles']) {
        allowedRoles = r.data['roles'];
        break;
      }
      r = r.parent;
    }
    const role = this.authService.getRole();
    if (role === 'developer' || allowedRoles.includes(role)) {
      return true;
    }
    return this.router.createUrlTree(['/home']);
  }
}
