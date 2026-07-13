module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended-type-checked',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs', 'src/api/schema.d.ts'],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: ['./tsconfig.json'],
    tsconfigRootDir: __dirname,
  },
  plugins: ['@typescript-eslint'],
  rules: {
    'no-restricted-syntax': [
      'error',
      {
        selector: "Literal[value=/^#[0-9A-Fa-f]{3,8}$/]",
        message:
          'Raw hex color detected. Use CSS custom properties (var(--token-name)) via the cn() utility and Tailwind semantic classes. Hex values are only permitted in src/styles/tokens.css.',
      },
    ],
    'no-restricted-properties': [
      'error',
      {
        object: 'style',
        property: 'color',
        message: 'Use className with Tailwind token classes instead of inline style.color.',
      },
    ],
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/no-explicit-any': 'error',
  },
}
