import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../services/auth.service';
import { LoadingService } from '../../../services/loading.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
  imports: [CommonModule, ReactiveFormsModule],
  standalone: true
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  errorMessage = '';
  isLoading = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private loadingService: LoadingService
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });
  }

  ngOnInit() {
    // Check if user is already logged in
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/home']);
    }
  }

  onSubmit() {
    if (this.loginForm.valid) {
      this.isLoading = true;
      this.loadingService.show('Signing you in...');
      this.errorMessage = '';

      const { email, password } = this.loginForm.value;

      this.authService.login(email, password).subscribe({
        next: (response) => {
          this.isLoading = false;
          this.loadingService.hide();
          
          if (response.success) {
            this.router.navigate(['/home']);
          } else {
            this.errorMessage = response.error || 'Login failed. Please try again.';
          }
        },
        error: (error) => {
          this.isLoading = false;
          this.loadingService.hide();
          this.errorMessage = 'An error occurred. Please try again.';
          console.error('Login error:', error);
        }
      });
    } else {
      this.markFormGroupTouched();
    }
  }

  private markFormGroupTouched() {
    Object.keys(this.loginForm.controls).forEach(key => {
      const control = this.loginForm.get(key);
      control?.markAsTouched();
    });
  }

  getErrorMessage(fieldName: string): string {
    const control = this.loginForm.get(fieldName);
    if (control?.hasError('required')) {
      return `${fieldName.charAt(0).toUpperCase() + fieldName.slice(1)} is required`;
    }
    if (control?.hasError('email')) {
      return 'Please enter a valid email address';
    }
    if (control?.hasError('minlength')) {
      return 'Password must be at least 6 characters long';
    }
    return '';
  }

  navigateToRegister() {
    this.router.navigate(['/register']);
  }
  navigateToDeveloperLogin() {
      this.authService.login('dev@example.com', 'devpassword').subscribe({
      next: (response) => {
        if (response.success) {
          this.router.navigate(['/home']);
        } else {
          this.errorMessage = response.error || 'Developer login failed. Please try again.';
        }
      },
      error: (error) => {
        console.error('Developer login error:', error);
      }
    });
  }
  navigateToAdminLogin() {
    this.authService.login('admin@example.com', 'adminPassword').subscribe({
      next: (response) => {
        if (response.success) {
          this.router.navigate(['/home']);
        } else {
          this.errorMessage = response.error || 'Admin login failed. Please try again.';
        }
      },
      error: (error) => {
        console.error('Admin login error:', error);
      }
    });
  }
  navigateToUserLogin() {
    this.authService.login('john.doe@example.com', 'password').subscribe({
      next: (response) => {
        if (response.success) {
          this.router.navigate(['/home']);
        } else {
          this.errorMessage = response.error || 'User login failed. Please try again.';
        }
      },
      error: (error) => {
        console.error('User login error:', error);
      }
    });
  }
}
