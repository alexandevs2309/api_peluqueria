import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

export interface FrontendLogEntry {
  level: 'info' | 'warn' | 'error';
  message: string;
  timestamp: string;
  url: string;
  context?: unknown;
}

const LOG_STORAGE_KEY = 'frontend_observability_logs';
const MAX_LOG_ENTRIES = 50;

@Injectable({
  providedIn: 'root'
})
export class FrontendObservabilityService {
  captureInfo(message: string, context?: unknown): void {
    this.capture('info', message, context);
  }

  captureWarn(message: string, context?: unknown): void {
    this.capture('warn', message, context);
  }

  captureError(message: string, context?: unknown): void {
    this.capture('error', message, context);
  }

  getLogs(): FrontendLogEntry[] {
    try {
      const stored = localStorage.getItem(LOG_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

    private capture(level: FrontendLogEntry['level'], message: string, context?: unknown): void {
        const entry: FrontendLogEntry = {
            level,
            message,
            timestamp: new Date().toISOString(),
            url: typeof window !== 'undefined' ? window.location.pathname : '',
            context: this.sanitizeContext(context)
        };

        this.writeToConsole(entry);
        if (!environment.production) {
            this.persist(entry);
        }
    }

  private persist(entry: FrontendLogEntry): void {
    try {
      const current = this.getLogs();
      const next = [entry, ...current].slice(0, MAX_LOG_ENTRIES);
      localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(next));
    } catch {
      // No bloquear la app si localStorage falla.
    }
  }

  private writeToConsole(entry: FrontendLogEntry): void {
    if (entry.level === 'error') {
      if (!environment.production) console.error('[frontend]', entry.message, entry.context);
      return;
    }

    if (!environment.production || entry.level === 'warn') {
      console.warn('[frontend]', entry.message, entry.context);
    }
  }

    private sanitizeContext(context: unknown): unknown {
        if (context instanceof Error) {
            return {
                name: context.name,
                message: context.message,
            };
        }

        return context;
    }
}
