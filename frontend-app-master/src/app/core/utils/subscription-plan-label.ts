export function getSubscriptionPlanLabel(...candidates: Array<unknown>): string {
    for (const candidate of candidates) {
        if (typeof candidate !== 'string') {
            continue;
        }

        const normalized = candidate.trim();
        if (!normalized) {
            continue;
        }

        const commercialName = normalizeCommercialPlanName(normalized);
        if (commercialName) {
            return commercialName;
        }

        return normalized;
    }

    return '-';
}

function normalizeCommercialPlanName(value: string): string | null {
    const key = value.trim().toLowerCase();
    const map: Record<string, string> = {
        free: 'Trial',
        basic: 'Basic',
        standard: 'Pro',
        premium: 'Business',
        enterprise: 'Enterprise',
        professional: 'Basic',
        business: 'Business',
        esencial: 'Basic',
        crecimiento: 'Pro',
        escala: 'Business',
        pro: 'Pro'
    };

    return map[key] || (key ? 'Trial' : null);
}
