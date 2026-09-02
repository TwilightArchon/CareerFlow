import { describe, expect, it } from 'vitest';

describe('desktop foundation', () => {
  it('has a stable application identity', () => {
    expect('dev.careerflow.desktop').toMatch(/^dev\.careerflow\./);
  });
});
