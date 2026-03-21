import { describe, it, expect } from 'vitest';
import fs from 'fs';

describe('Monorepo Integration', () => {
  it('turbo.json exists with pipeline', () => {
    const turbo = JSON.parse(fs.readFileSync('turbo.json', 'utf-8'));
    expect(turbo.tasks || turbo.pipeline).toBeDefined();
  });

  it('docker-compose.yml has postgres + redis + localstack', () => {
    const compose = fs.readFileSync('docker-compose.yml', 'utf-8');
    expect(compose).toContain('postgres');
    expect(compose).toContain('redis');
    expect(compose).toContain('localstack');
  });

  it('GitHub Actions CI exists', () => {
    expect(fs.existsSync('.github/workflows/ci.yml')).toBe(true);
  });

  it('.env.example has required variables', () => {
    const env = fs.readFileSync('.env.example', 'utf-8');
    ['DATABASE_URL', 'REDIS_URL', 'SP_API_CLIENT_ID', 'ANTHROPIC_API_KEY'].forEach(v => {
      expect(env).toContain(v);
    });
  });
});
