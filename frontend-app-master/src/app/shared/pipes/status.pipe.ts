import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'status',
  standalone: true
})
export class StatusPipe implements PipeTransform {
  transform(value: boolean | string | null): string {
    if (value === null || value === undefined) return 'Desconocido';
    
    if (typeof value === 'boolean') {
      return value ? 'Activo' : 'Inactivo';
    }
    
    const stringValue = value.toString().toLowerCase();
    switch (stringValue) {
      case 'active':
      case 'true':
      case '1':
        return 'Activo';
      case 'inactive':
      case 'false':
      case '0':
        return 'Inactivo';
      case 'pending':
        return 'Pendiente';
      case 'suspended':
        return 'Suspendido';
      default:
        return value.toString();
    }
  }
}