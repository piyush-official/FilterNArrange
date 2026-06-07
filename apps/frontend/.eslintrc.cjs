module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 2023, sourceType: 'module', ecmaFeatures: { jsx: true } },
  plugins: ['boundaries', 'import', 'react'],
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
  ignorePatterns: ['dist', 'src/shared/api/generated', 'tests'],
};
