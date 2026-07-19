import { Pipe, PipeTransform } from '@angular/core';
import { getRoleDisplayLabel } from '../../core/utils/role-normalizer';

@Pipe({
  name: 'role',
  standalone: true
})
export class RolePipe implements PipeTransform {
  transform(value: string | null, businessRole?: string | null, businessRoleDisplay?: string | null): string {
    return getRoleDisplayLabel(value, businessRole, businessRoleDisplay);
  }
}
