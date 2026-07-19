import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'spanishDate',
  standalone: true
})
export class SpanishDatePipe implements PipeTransform {
  private months = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
  ];

  transform(value: string | Date | null): string {
    if (!value) return '';
    
    const date = new Date(value);
    if (isNaN(date.getTime())) return '';

    const day = date.getDate();
    const month = this.months[date.getMonth()];
    const year = date.getFullYear();

    return `${day} de ${month} de ${year}`;
  }
}