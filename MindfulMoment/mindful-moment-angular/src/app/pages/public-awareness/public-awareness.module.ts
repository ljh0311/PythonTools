import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';

import { PublicAwarenessComponent } from './public-awareness.component';

const routes: Routes = [
  { path: '', component: PublicAwarenessComponent }
];

@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(routes),
    PublicAwarenessComponent
  ]
})
export class PublicAwarenessModule { }
