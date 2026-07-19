import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

export interface AdminErrorLogEntry {
    component: string;
    context: string;
    message: string;
    timestamp: string;
    statusCode?: number;
    url?: string;
    details?: unknown;
}

@Injectable({
    providedIn: 'root'
})
export class AdminErrorLogService {
    private readonly storageKey = 'admin_error_logs';
    private readonly maxEntries = 50;

    log(component: string, context: string, error: unknown, details?: unknown): void {
        const entry = this.buildEntry(component, context, error, details);

        try {
            const entries = this.getLogs();
            entries.unshift(entry);
            sessionStorage.setItem(this.storageKey, JSON.stringify(entries.slice(0, this.maxEntries)));
        } catch {
            // Ignore storage failures and still log to console.
        }

        if (!environment.production) console.error(`[${component}] ${context}`, entry);
    }

    getLogs(): AdminErrorLogEntry[] {
        try {
            const raw = sessionStorage.getItem(this.storageKey);
            if (!raw) return [];

            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    }

    private buildEntry(component: string, context: string, error: unknown, details?: unknown): AdminErrorLogEntry {
        const source = error as {
            message?: string;
            status?: number;
            url?: string;
            error?: unknown;
        } | null;

        return {
            component,
            context,
            timestamp: new Date().toISOString(),
            message: this.extractMessage(error),
            statusCode: source?.status,
            url: source?.url,
            details: details ?? source?.error
        };
    }

    private extractMessage(error: unknown): string {
        if (!error) return 'Unknown error';
        if (typeof error === 'string') return error;

        const source = error as {
            message?: string;
            error?: { message?: string; error?: string };
        };

        return source?.error?.message || source?.error?.error || source?.message || 'Unknown error';
    }
}
