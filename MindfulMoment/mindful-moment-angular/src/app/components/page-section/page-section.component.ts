import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-page-section',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './page-section.component.html',
  styleUrls: ['./page-section.component.scss']
})
export class PageSectionComponent {
  @Input() title = '';
  @Input() icon = 'fas fa-folder';
}
