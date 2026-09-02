export type Platform = 'synthetic' | 'workday' | 'greenhouse' | 'lever' | 'unknown';

export interface AdapterDetection {
  platform: Platform;
  confidence: number;
  signals: string[];
}

export interface ObservedControl {
  controlId: string;
  label: string;
  kind: 'text' | 'email' | 'tel' | 'select' | 'checkbox' | 'radio' | 'file' | 'textarea';
  required: boolean;
  sensitive: boolean;
  autocomplete?: string;
}

export interface AtsAdapter {
  readonly platform: Platform;
  detect(url: URL, html: string): AdapterDetection;
  inspect(): Promise<ObservedControl[]>;
}
