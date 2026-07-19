import { RuntimeConfigValidatorService } from './runtime-config-validator.service';

describe('RuntimeConfigValidatorService', () => {
    let service: RuntimeConfigValidatorService;

    beforeEach(() => {
        service = new RuntimeConfigValidatorService();
    });

    it('should validate the current development config without errors', () => {
        const result = service.validateRuntimeConfig();

        expect(result.valid).toBeTrue();
        expect(result.errors.length).toBe(0);
    });

    it('should detect localhost URLs as local URLs', () => {
        expect((service as any).isLocalUrl('http://localhost/api')).toBeTrue();
        expect((service as any).isLocalUrl('https://127.0.0.1/ws')).toBeTrue();
        expect((service as any).isLocalUrl('https://api.example.com')).toBeFalse();
    });

    it('should detect Stripe test publishable keys', () => {
        expect((service as any).isTestStripeKey('pk_test_123')).toBeTrue();
        expect((service as any).isTestStripeKey('pk_live_123')).toBeFalse();
        expect((service as any).isTestStripeKey('')).toBeFalse();
    });
});
