// Flat config (ESLint 9) equivalent of the legacy .eslintrc.cjs.
// Same boundaries rules: enforce app → pages → features → shared layering,
// disallow cross-feature imports.
import tsParser from '@typescript-eslint/parser';
import boundaries from 'eslint-plugin-boundaries';
import importPlugin from 'eslint-plugin-import';
import reactPlugin from 'eslint-plugin-react';

export default [
  {
    ignores: ['dist/**', 'src/shared/api/generated/**', 'tests/**', 'node_modules/**'],
  },
  {
    files: ['src/**/*.{ts,tsx,js,jsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: 2023, sourceType: 'module', ecmaFeatures: { jsx: true } },
    },
    plugins: {
      boundaries,
      import: importPlugin,
      react: reactPlugin,
    },
    settings: {
      react: { version: 'detect' },
      'boundaries/elements': [
        { type: 'app',      pattern: 'src/app/**' },
        { type: 'pages',    pattern: 'src/pages/**' },
        { type: 'features', pattern: 'src/features/*' },
        { type: 'shared',   pattern: 'src/shared/**' },
      ],
    },
    rules: {
      'boundaries/element-types': ['error', {
        default: 'disallow',
        rules: [
          { from: 'app',      allow: ['pages', 'features', 'shared'] },
          { from: 'pages',    allow: ['features', 'shared'] },
          { from: 'features', allow: ['shared'] },
          { from: 'shared',   allow: ['shared'] },
        ],
      }],
      'boundaries/no-private': ['error', { allowUncles: false }],
      'import/no-default-export': 'off',
    },
  },
];
