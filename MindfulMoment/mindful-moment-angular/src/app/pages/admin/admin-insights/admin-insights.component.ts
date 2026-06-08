import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-admin-insights',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './admin-insights.component.html',
  styleUrls: ['./admin-insights.component.scss']
})
export class AdminInsightsComponent {
  constructor() {}
}
