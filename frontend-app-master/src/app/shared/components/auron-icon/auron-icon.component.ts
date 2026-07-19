import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, Input, OnChanges, inject, signal } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { catchError, map, of } from 'rxjs';

@Component({
  selector: 'auron-icon',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span
      class="auron-icon"
      [style.width.px]="size"
      [style.height.px]="size"
      [style.color]="color || 'currentColor'"
      [innerHTML]="svg()"
      aria-hidden="true"
    ></span>
  `,
  styles: [`
    .auron-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      line-height: 0;
    }

    .auron-icon :where(svg) {
      width: 100%;
      height: 100%;
      display: block;
    }
  `],
})
export class AuronIconComponent implements OnChanges {
  @Input({ required: true }) name = '';
  @Input() size = 20;
  @Input() color?: string;

  private http = inject(HttpClient);
  private sanitizer = inject(DomSanitizer);
  protected svg = signal<SafeHtml>('');

  ngOnChanges(): void {
    if (!this.name) {
      this.svg.set('');
      return;
    }

    this.http.get(`assets/icons/${this.name}.svg`, { responseType: 'text' }).pipe(
      map((svg) => this.sanitizer.bypassSecurityTrustHtml(svg)),
      catchError(() => of(this.sanitizer.bypassSecurityTrustHtml('')))
    ).subscribe((svg) => this.svg.set(svg));
  }
}
