import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Next.js Web App Setup', () => {
  const webRoot = path.resolve(__dirname, '..');

  it('has package.json with correct name @repo/web', () => {
    const pkg = JSON.parse(fs.readFileSync(path.join(webRoot, 'package.json'), 'utf-8'));
    expect(pkg.name).toBe('@repo/web');
    expect(pkg.dependencies).toHaveProperty('next');
    expect(pkg.dependencies).toHaveProperty('react');
  });

  it('has Next.js app router structure', () => {
    expect(fs.existsSync(path.join(webRoot, 'src/app/layout.tsx'))).toBe(true);
    expect(fs.existsSync(path.join(webRoot, 'src/app/page.tsx'))).toBe(true);
  });

  it('has Tailwind config with Joyful Tech design tokens', () => {
    const config = fs.readFileSync(path.join(webRoot, 'tailwind.config.ts'), 'utf-8');
    expect(config).toContain('primary-pop');
    expect(config).toContain('#3b82f6');
    expect(config).toContain('accent-joy');
    expect(config).toContain('#f472b6');
    expect(config).toContain('Fredoka');
    expect(config).toContain('Inter');
  });

  it('has shadcn/ui components directory', () => {
    expect(fs.existsSync(path.join(webRoot, 'src/components/ui'))).toBe(true);
  });

  it('has path aliases configured', () => {
    const tsconfig = JSON.parse(fs.readFileSync(path.join(webRoot, 'tsconfig.json'), 'utf-8'));
    expect(tsconfig.compilerOptions.paths).toHaveProperty('@/*');
  });

  it('has required dependencies', () => {
    const pkg = JSON.parse(fs.readFileSync(path.join(webRoot, 'package.json'), 'utf-8'));
    const all = { ...pkg.dependencies, ...pkg.devDependencies };
    ['@tanstack/react-query', 'zustand', 'axios', 'zod', 'react-hook-form'].forEach(dep => {
      expect(all).toHaveProperty(dep);
    });
  });

  it('has Fredoka and Inter fonts in layout', () => {
    const layout = fs.readFileSync(path.join(webRoot, 'src/app/layout.tsx'), 'utf-8');
    expect(layout).toContain('Fredoka');
    expect(layout).toContain('Inter');
  });

  it('has vitest configured', () => {
    expect(fs.existsSync(path.join(webRoot, 'vitest.config.ts'))).toBe(true);
  });
});
