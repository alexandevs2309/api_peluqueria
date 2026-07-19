import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

export interface AccessDeniedDialogInfo {
  title: string;
  message: string;
  primaryButtonLabel?: string;
  primaryButtonAction?: () => void;
  secondaryButtonLabel?: string;
  secondaryButtonAction?: () => void;
  icon?: string;
  iconColor?: string;
  iconBgColor?: string;
}

@Injectable({ providedIn: 'root' })
export class AccessDeniedDialogService {
  private dialogSubject = new Subject<AccessDeniedDialogInfo | null>();
  dialog$ = this.dialogSubject.asObservable();

  show(info: AccessDeniedDialogInfo) {
    this.dialogSubject.next(info);
  }

  dismiss() {
    this.dialogSubject.next(null);
  }
}
