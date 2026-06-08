import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Routes } from '@angular/router';

import { CommunityComponent } from './community.component';

const routes: Routes = [{ path: '', component: CommunityComponent }];

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    RouterModule.forChild(routes),
    CommunityComponent
  ]
})

export class CommunityModule {}
