import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from './guards/auth.guard';
import { RoleGuard } from './guards/role.guard';
import { LoginComponent } from './pages/auth/login/login.component';
import { RegisterComponent } from './pages/auth/register/register.component';
import { HomeComponent } from './pages/home/home.component';
import { FocusComponent } from './pages/focus/focus.component';
import { CommunityComponent } from './pages/community/community.component';
import { CommunityDetailComponent } from './pages/community/community-detail/community-detail.component';
import { InsightsComponent } from './pages/insights/insights.component';
import { PublicAwarenessComponent } from './pages/public-awareness/public-awareness.component';
import { ProfileComponent } from './pages/profile/profile.component';
import { SettingsComponent } from './pages/settings/settings.component';
import { AdminUsersComponent } from './pages/admin/admin-users/admin-users.component';
import { AdminInsightsComponent } from './pages/admin/admin-insights/admin-insights.component';
import { BusArrivalsComponent } from './pages/bus/bus-arrivals.component';

const routes: Routes = [
  // Public routes
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  
  // Protected routes
  { 
    path: 'home', 
    component: HomeComponent,
    canActivate: [AuthGuard]
  },
  { 
    path: 'focus', 
    component: FocusComponent,
    canActivate: [AuthGuard]
  },
  {
    path: 'community',
    canActivate: [AuthGuard],
    children: [
      { path: '', component: CommunityComponent },
      { path: ':id', component: CommunityDetailComponent }
    ]
  },
  { 
    path: 'insights', 
    component: InsightsComponent,
    canActivate: [AuthGuard]
  },
  { 
    path: 'public-awareness', 
    component: PublicAwarenessComponent,
    canActivate: [AuthGuard]
  },
  {
    path: 'bus',
    component: BusArrivalsComponent,
    canActivate: [AuthGuard]
  },
  { 
    path: 'profile', 
    component: ProfileComponent,
    canActivate: [AuthGuard]
  },
  { 
    path: 'settings', 
    component: SettingsComponent,
    canActivate: [AuthGuard]
  },

  // Admin-only routes
  {
    path: 'admin',
    canActivate: [AuthGuard, RoleGuard],
    data: { roles: ['admin', 'developer'] },
    children: [
      { path: 'users', component: AdminUsersComponent },
      { path: 'insights', component: AdminInsightsComponent },
      { path: '', redirectTo: 'users', pathMatch: 'full' }
    ]
  },
  
  // Wildcard route
  { path: '**', redirectTo: '/login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {
    enableTracing: false, // Set to true for debugging
    scrollPositionRestoration: 'top',
    anchorScrolling: 'enabled'
  })],
  exports: [RouterModule]
})
export class AppRoutingModule { }
