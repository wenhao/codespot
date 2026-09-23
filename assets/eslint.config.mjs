// codespot ESLint deep-layer config: SonarJS rules (recommended) + a small
// eslint core quality subset. eslint-plugin-oxlint's disable list goes LAST —
// it turns off rules the fast oxlint layer already covers, so findings never
// duplicate. Type-aware rules are out of scope for M1.
import sonarjs from 'eslint-plugin-sonarjs';
import oxlint from 'eslint-plugin-oxlint';

export default [
  {
    files: ['**/*.js', '**/*.jsx', '**/*.mjs', '**/*.cjs', '**/*.ts', '**/*.mts', '**/*.cts', '**/*.tsx'],
  },
  sonarjs.configs.recommended,
  {
    rules: {
      // duplicate of the unused-vars family the fast oxlint layer already owns
      'sonarjs/no-unused-vars': 'off',
      'no-unused-vars': 'warn',
      'no-constant-condition': 'warn',
      'no-eval': 'warn',
      eqeqeq: ['warn', 'smart'],
    },
  },
  ...oxlint.configs['flat/recommended'],
];
