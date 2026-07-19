import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

export interface ErrorDialogInfo {
  message: string;
  retryLabel?: string;
  retry?: () => void;
}

@Injectable({ providedIn: 'root' })
export class ErrorDialogService {
  private errorSubject = new Subject<ErrorDialogInfo | null>();
  error$ = this.errorSubject.asObservable();

  show(info: ErrorDialogInfo) {
    this.errorSubject.next(info);
  }

  dismiss() {
    this.errorSubject.next(null);
  }
}
