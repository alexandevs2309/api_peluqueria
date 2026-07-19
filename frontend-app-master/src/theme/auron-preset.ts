import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

export const AuronPreset = definePreset(Aura, {
    semantic: {
        primary: {
            50: '{blue.50}',
            100: '{blue.100}',
            200: '{blue.200}',
            300: '{blue.300}',
            400: '#4C7EE8',
            500: '#1A56DB',
            600: '#1544AD',
            700: '#103585',
            800: '#0B275F',
            900: '#071A3D',
            950: '#040F24',
        },
        colorScheme: {
            dark: {
                surface: {
                    0: '#0B0F16',
                    50: '#111827',
                    100: '#161B26',
                    200: '#1A2130',
                    300: 'rgba(255,255,255,0.07)',
                    400: '#94A3B8',
                    500: '#64748B',
                    900: '#F8FAFC',
                },
                content: {
                    background: '#161B26',
                    borderColor: 'rgba(255,255,255,0.07)',
                },
            },
            light: {
                surface: {
                    0: '#FFFFFF',
                    50: '#F8FAFC',
                    100: '#F1F5F9',
                    300: 'rgba(15,23,42,0.08)',
                    400: '#475569',
                    500: '#94A3B8',
                    900: '#0F172A',
                },
            },
        },
    },
    components: {
        button: {
            root: {
                borderRadius: '999px',
            },
        },
        card: {
            root: {
                borderRadius: '20px',
            },
        },
        inputtext: {
            root: {
                borderRadius: '12px',
            },
        },
    },
});
