import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OnboardingTourOverlayComponent } from './onboarding-tour-overlay.component';

@NgModule({
    imports: [CommonModule, OnboardingTourOverlayComponent],
    exports: [OnboardingTourOverlayComponent]
})
export class OnboardingTourModule {}
