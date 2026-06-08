import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-page-back-bar',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './page-back-bar.component.html',
  styleUrls: ['./page-back-bar.component.scss']
})
export class PageBackBarComponent {
  @Input() backUrl = '/community';
  @Input() title?: string;
}
