import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface TutorialDto {
  id: number;
  module: string;
  module_label: string;
  title: string;
  description: string;
  video_url: string;
  thumbnail_url: string;
  duration: string;
  order: number;
  is_published: boolean;
}

export function getYouTubeThumbnail(url: string): string | null {
  try {
    const u = new URL(url);
    let id: string | null = null;
    if (u.hostname === 'youtu.be') {
      id = u.pathname.slice(1).split('/')[0].split('?')[0];
    } else if (u.hostname.includes('youtube.com')) {
      id = u.searchParams.get('v');
    }
    if (id) return `https://img.youtube.com/vi/${id}/maxresdefault.jpg`;
    return null;
  } catch {
    return null;
  }
}

function isYouTubeUrl(url: string): boolean {
  try {
    const u = new URL(url);
    return u.hostname.includes('youtube.com') || u.hostname === 'youtu.be';
  } catch {
    return false;
  }
}

@Injectable({ providedIn: 'root' })
export class TutorialsService extends BaseApiService {
  private readonly endpoint = API_CONFIG.ENDPOINTS.TUTORIALS.BASE;

  getAll(module?: string): Observable<TutorialDto[]> {
    const params: any = {};
    if (module) params.module = module;
    return this.get<TutorialDto[]>(this.endpoint, params);
  }
}
