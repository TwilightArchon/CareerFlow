export class CommandReplayCache {
  private readonly responses = new Map<string, string>();

  constructor(private readonly maxEntries = 500) {
    if (!Number.isInteger(maxEntries) || maxEntries < 1) {
      throw new Error('Command replay cache size must be a positive integer');
    }
  }

  get(commandId: string): string | undefined {
    return this.responses.get(commandId);
  }

  remember(commandId: string, response: string): void {
    if (this.responses.has(commandId)) return;
    this.responses.set(commandId, response);
    while (this.responses.size > this.maxEntries) {
      const oldest = this.responses.keys().next().value as string | undefined;
      if (!oldest) break;
      this.responses.delete(oldest);
    }
  }
}
