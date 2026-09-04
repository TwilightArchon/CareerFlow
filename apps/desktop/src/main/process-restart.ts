export interface RestartAttempt {
  attempt: number;
  delayMs: number;
}

export class RestartBudget {
  private used = 0;

  constructor(private readonly delaysMs: readonly number[] = [250, 1_000, 3_000]) {
    if (delaysMs.length === 0 || delaysMs.some((delay) => !Number.isFinite(delay) || delay < 0)) {
      throw new Error('Restart delays must contain non-negative finite values');
    }
  }

  claim(): RestartAttempt | null {
    const delayMs = this.delaysMs[this.used];
    if (delayMs === undefined) return null;
    this.used += 1;
    return { attempt: this.used, delayMs };
  }

  reset(): void {
    this.used = 0;
  }
}
