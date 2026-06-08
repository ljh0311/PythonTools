import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { FlexLayoutModule } from '@angular/flex-layout';

// Angular Material Modules
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule } from '@angular/material/dialog';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import { MatListModule } from '@angular/material/list';
import { MatStepperModule } from '@angular/material/stepper';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatRadioModule } from '@angular/material/radio';
import { MatSliderModule } from '@angular/material/slider';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatBottomSheetModule } from '@angular/material/bottom-sheet';

// App Components
import { AppComponent } from './app.component';
import { AppRoutingModule } from './app-routing.module';

// Shared Components
import { HeaderComponent } from './components/header/header.component';
import { BottomNavComponent } from './components/bottom-nav/bottom-nav.component';
import { DevBoxComponent } from './components/dev-box/dev-box.component';
import { LoadingOverlayComponent } from './components/loading-overlay/loading-overlay.component';
import { ToastContainerComponent } from './components/toast-container/toast-container.component';

// Page Components (Standalone)
import { LoginComponent } from './pages/auth/login/login.component';
import { RegisterComponent } from './pages/auth/register/register.component';
import { HomeComponent } from './pages/home/home.component';
import { FocusComponent } from './pages/focus/focus.component';
import { CommunityComponent } from './pages/community/community.component';
import { InsightsComponent } from './pages/insights/insights.component';
import { PublicAwarenessComponent } from './pages/public-awareness/public-awareness.component';
import { ProfileComponent } from './pages/profile/profile.component';
import { SettingsComponent } from './pages/settings/settings.component';
import { CommunityDetailComponent } from './pages/community/community-detail/community-detail.component';
import { AdminUsersComponent } from './pages/admin/admin-users/admin-users.component';
import { AdminInsightsComponent } from './pages/admin/admin-insights/admin-insights.component';
import { BusArrivalsComponent } from './pages/bus/bus-arrivals.component';

// Services
import { AuthService } from './services/auth.service';
import { DataService } from './services/data.service';
import { LoadingService } from './services/loading.service';
import { ErrorHandler } from '@angular/core';
import { GlobalErrorHandler } from './services/error-handler.service';

@NgModule({
  declarations: [
    AppComponent,
    HeaderComponent,
    LoadingOverlayComponent,
    ToastContainerComponent
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    FlexLayoutModule,
    
    // Angular Material
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
    MatTabsModule,
    MatChipsModule,
    MatBadgeModule,
    MatDividerModule,
    MatListModule,
    MatStepperModule,
    MatCheckboxModule,
    MatRadioModule,
    MatSliderModule,
    MatSlideToggleModule,
    MatExpansionModule,
    MatTooltipModule,
    MatSidenavModule,
    MatBottomSheetModule,
    
    // Standalone Page Components
    LoginComponent,
    RegisterComponent,
    HomeComponent,
    FocusComponent,
    CommunityComponent,
    InsightsComponent,
    PublicAwarenessComponent,
    BusArrivalsComponent,
    ProfileComponent,
    SettingsComponent,
    CommunityDetailComponent,
    AdminUsersComponent,
    AdminInsightsComponent,
    
    // Standalone Shared Components
    BottomNavComponent,
    DevBoxComponent,

    AppRoutingModule
  ],
  providers: [
    AuthService,
    DataService,
    LoadingService,
    {
      provide: ErrorHandler,
      useClass: GlobalErrorHandler
    }
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
