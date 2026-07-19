import { Injectable, signal, computed } from '@angular/core';
import { Observable, tap, of } from 'rxjs';
import { finalize, shareReplay } from 'rxjs/operators';
import { BaseApiService } from '../base-api.service';
import { safeGetItem } from '../../utils/storage';

export interface Branch {
  id: number;
  name: string;
  address: string | null;
  is_main: boolean;
  is_active: boolean;
  employee_count: number;
}

@Injectable({ providedIn: 'root' })
export class BranchService extends BaseApiService {
  activeBranch = signal<Branch | null>(null);
  activeBranchId = computed(() => this.activeBranch()?.id || null);
  branches = signal<Branch[]>([]);
  private branchesRequest$: Observable<Branch[]> | null = null;
  constructor() {
    super();
    try {
      const storedBranch = localStorage.getItem('activeBranch');
      if (storedBranch) {
        this.activeBranch.set(JSON.parse(storedBranch));
      }
    } catch (e) {}
  }

  getAll(): Observable<Branch[]> {
    return this.get<Branch[]>('/settings/branches/');
  }

  getById(id: number): Observable<Branch> {
    return this.get<Branch>(`/settings/branches/${id}/`);
  }

  create(data: Partial<Branch>): Observable<Branch> {
    return this.post<Branch>('/settings/branches/', data);
  }

  update(id: number, data: Partial<Branch>): Observable<Branch> {
    return this.patch<Branch>(`/settings/branches/${id}/`, data);
  }

  remove(id: number): Observable<void> {
    return this.delete(`/settings/branches/${id}/`);
  }

  loadBranches(force = false): Observable<Branch[]> {
    if (!force && this.branches().length > 0) {
      return of(this.branches());
    }
    if (this.branchesRequest$) {
      return this.branchesRequest$;
    }

    this.branchesRequest$ = this.getAll().pipe(
      tap((branchesList) => {
        this.branches.set(branchesList);
        
        // Determinar si el usuario es un empleado con sucursal asignada
        const userStr = safeGetItem('user');
        let employeeBranchId: number | null = null;
        if (userStr) {
          try {
            const userObj = JSON.parse(userStr);
            const role = userObj.role;
            if (role !== 'CLIENT_ADMIN' && role !== 'SUPER_ADMIN' && role !== 'Client-Admin' && role !== 'SuperAdmin' && userObj.branch_id) {
              employeeBranchId = userObj.branch_id;
            }
          } catch (e) {}
        }

        let selected: Branch | null = null;
        if (employeeBranchId) {
          selected = branchesList.find(b => b.id === employeeBranchId) || null;
        } else {
          const storedBranch = localStorage.getItem('activeBranch');
          if (storedBranch) {
            try {
              const parsed = JSON.parse(storedBranch) as Branch;
              selected = branchesList.find(b => b.id === parsed.id) || null;
            } catch (e) {
              selected = null;
            }
          }
          if (!selected && branchesList.length > 0) {
            selected = branchesList.find(b => b.is_main) || branchesList[0];
          }
        }

        this.activeBranch.set(selected);
        if (selected) {
          localStorage.setItem('activeBranch', JSON.stringify(selected));
        } else {
          localStorage.removeItem('activeBranch');
        }
      }),
      finalize(() => {
        this.branchesRequest$ = null;
      }),
      shareReplay(1)
    );

    return this.branchesRequest$;
  }

  selectBranch(branch: Branch | null): void {
    this.activeBranch.set(branch);
    if (branch) {
      localStorage.setItem('activeBranch', JSON.stringify(branch));
    } else {
      localStorage.removeItem('activeBranch');
    }
  }
}
