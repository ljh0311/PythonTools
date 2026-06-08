import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../services/auth.service';
import { LoadingService } from '../../../services/loading.service';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss'],
  imports: [CommonModule, ReactiveFormsModule],
  standalone: true
})
export class RegisterComponent implements OnInit {
  registerForm: FormGroup;
  errorMessage = '';
  isLoading = false;
  showPassword = false;
  showConfirmPassword = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private loadingService: LoadingService
  ) {
    this.registerForm = this.fb.group({
      firstName: ['', [Validators.required, Validators.minLength(2)]],
      lastName: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]],
      community: ['singapore', [Validators.required]],
      agreeToTerms: [false, [Validators.requiredTrue]]
    }, { validators: this.passwordMatchValidator });
  }

  ngOnInit() {
    // Check if user is already logged in
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/home']);
    }
  }

  passwordMatchValidator(form: FormGroup) {
    const password = form.get('password');
    const confirmPassword = form.get('confirmPassword');
    
    if (password && confirmPassword && password.value !== confirmPassword.value) {
      confirmPassword.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }
    
    return null;
  }

  onSubmit() {
    if (this.registerForm.valid) {
      this.isLoading = true;
      this.loadingService.show('Creating your account...');
      this.errorMessage = '';

      const { firstName, lastName, email, password, community } = this.registerForm.value;

      const userData = {
        firstName,
        lastName,
        email,
        password,
        community,
        preferences: {
          language: 'en',
          alertFrequency: 5,
          primaryGoal: 'mindfulness',
          notifications: true,
          location: true,
          screenTime: true,
          focusMode: true,
          theme: 'light',
          accessibility: {
            highContrast: false,
            largeText: false,
            screenReader: false
          }
        },
        stats: {
          totalSessions: 0,
          totalMindfulMinutes: 0,
          totalSafetyAlerts: 0,
          totalSocialEngagements: 0,
          joinDate: new Date().toISOString(),
          lastActive: new Date().toISOString(),
          focusSessionStats: {
            totalPublicFocusTime: 0,
            totalSocialInteractions: 0,
            phoneUsageReduction: 0,
            mindfulMoments: 0
          },
          publicAwarenessStats: {
            totalPublicTime: 0,
            safetyAlerts: 0,
            socialPrompts: 0,
            mindfulScore: 0
          }
        },
        achievements: [],
        badges: [],
        points: 0,
        level: 1,
        homeSettings: {
          wifiNetworks: [],
          location: null,
          isConfigured: false
        },
        publicAwarenessSettings: {
          isEnabled: true,
          alertFrequency: 5,
          socialPrompts: true,
          safetyAlerts: true
        },
        joinDate: new Date().toISOString(),
        lastActive: new Date().toISOString()
      };

      this.authService.register(userData).subscribe({
        next: (response) => {
          this.isLoading = false;
          this.loadingService.hide();
          
          if (response.success) {
            this.router.navigate(['/home']);
          } else {
            this.errorMessage = response.error || 'Registration failed. Please try again.';
          }
        },
        error: (error) => {
          this.isLoading = false;
          this.loadingService.hide();
          this.errorMessage = 'An error occurred. Please try again.';
          console.error('Registration error:', error);
        }
      });
    } else {
      this.markFormGroupTouched();
    }
  }

  private markFormGroupTouched() {
    Object.keys(this.registerForm.controls).forEach(key => {
      const control = this.registerForm.get(key);
      control?.markAsTouched();
    });
  }

  getErrorMessage(fieldName: string): string {
    const control = this.registerForm.get(fieldName);
    if (control?.hasError('required')) {
      return `${fieldName.charAt(0).toUpperCase() + fieldName.slice(1)} is required`;
    }
    if (control?.hasError('email')) {
      return 'Please enter a valid email address';
    }
    if (control?.hasError('minlength')) {
      return `${fieldName.charAt(0).toUpperCase() + fieldName.slice(1)} must be at least ${control.errors?.['minlength'].requiredLength} characters long`;
    }
    if (control?.hasError('passwordMismatch')) {
      return 'Passwords do not match';
    }
    if (control?.hasError('requiredTrue')) {
      return 'You must agree to the terms and conditions';
    }
    return '';
  }

  togglePasswordVisibility() {
    this.showPassword = !this.showPassword;
  }

  toggleConfirmPasswordVisibility() {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  navigateToLogin() {
    this.router.navigate(['/login']);
  }
}
