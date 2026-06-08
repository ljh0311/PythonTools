import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DevBoxComponent } from './dev-box.component';

describe('DevBoxComponent', () => {
  let component: DevBoxComponent;
  let fixture: ComponentFixture<DevBoxComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DevBoxComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(DevBoxComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
