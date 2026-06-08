import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';

import { FocusComponent } from './focus.component';

const routes: Routes = [{ path: '', component: FocusComponent }];

@NgModule({
  imports: [CommonModule, RouterModule.forChild(routes), FocusComponent],
})
export class FocusModule {}
