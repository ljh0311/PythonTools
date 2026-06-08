import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';

import { InsightsComponent } from './insights.component';

const routes: Routes = [
  { path: '', component: InsightsComponent }
];

@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(routes),
    InsightsComponent
  ]
})
export class InsightsModule { }
