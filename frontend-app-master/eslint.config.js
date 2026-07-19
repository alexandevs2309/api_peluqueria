import angular from '@angular-eslint/eslint-plugin';
import angularTemplate from '@angular-eslint/eslint-plugin-template';
import angularParser from '@angular-eslint/template-parser';
import tseslint from 'typescript-eslint';
import tsParser from '@typescript-eslint/parser';
import prettier from 'eslint-plugin-prettier';

export default [
    {
        ignores: ['**/dist/**'],
    },
    ...tseslint.configs.recommended.map(c => ({
        ...c,
        files: ['**/*.ts'],
    })),
    {
        files: ['**/*.ts'],
        plugins: {
            '@angular-eslint': angular,
            prettier,
        },
        rules: {
            'padding-line-between-statements': 'off',
            '@angular-eslint/component-selector': [
                'warn',
                {
                    type: 'element',
                    prefix: ['app', 'p'],
                    style: 'kebab-case',
                },
            ],
            '@angular-eslint/directive-selector': [
                'warn',
                {
                    type: 'attribute',
                    prefix: ['app', 'p'],
                    style: 'camelCase',
                },
            ],
            '@angular-eslint/component-class-suffix': [
                'error',
                {
                    suffixes: [''],
                },
            ],
            '@angular-eslint/no-host-metadata-property': 'off',
            '@angular-eslint/no-output-on-prefix': 'off',
            '@typescript-eslint/ban-types': 'off',
            '@typescript-eslint/no-explicit-any': 'off',
            '@typescript-eslint/no-inferrable-types': 'off',
            'arrow-body-style': ['error', 'as-needed'],
            curly: 0,
            '@typescript-eslint/member-ordering': [
                'error',
                {
                    default: ['public-static-field', 'static-field', 'instance-field', 'public-instance-method', 'public-static-field'],
                },
            ],
            'no-console': 0,
            'prefer-const': 0,
        },
    },
    {
        files: ['**/*.html'],
        plugins: {
            '@angular-eslint/template': angularTemplate,
        },
        languageOptions: {
            parser: angularParser,
        },
        rules: {
            ...angularTemplate.configs.recommended.rules,
        },
    },
];
