import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CommunityGroup } from '../../models/community-group.model';

export type GroupCardMode = 'managed' | 'joined' | 'available';

@Component({
  selector: 'app-group-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './group-card.component.html',
  styleUrls: ['./group-card.component.scss']
})
export class GroupCardComponent {
  @Input() group!: CommunityGroup;
  @Input() mode: GroupCardMode = 'available';
  @Input() pendingRequestsCount = 0;

  @Output() view = new EventEmitter<CommunityGroup>();
  @Output() join = new EventEmitter<CommunityGroup>();
  @Output() leave = new EventEmitter<CommunityGroup>();
  @Output() edit = new EventEmitter<CommunityGroup>();
  @Output() delete = new EventEmitter<CommunityGroup>();
  @Output() manageRequests = new EventEmitter<CommunityGroup>();

  onView(e: Event, g: CommunityGroup) {
    e.stopPropagation();
    this.view.emit(g);
  }

  onJoin(e: Event, g: CommunityGroup) {
    e.stopPropagation();
    this.join.emit(g);
  }

  onLeave(e: Event, g: CommunityGroup) {
    e.stopPropagation();
    this.leave.emit(g);
  }

  onEdit(e: Event, g: CommunityGroup) {
    e.stopPropagation();
    this.edit.emit(g);
  }

  onDelete(e: Event, g: CommunityGroup) {
    e.stopPropagation();
    this.delete.emit(g);
  }

  onManageRequests(e: Event, g: CommunityGroup) {
    e.stopPropagation();
    this.manageRequests.emit(g);
  }

  onCardClick(g: CommunityGroup) {
    if (this.mode !== 'managed') {
      this.view.emit(g);
    }
  }
}
