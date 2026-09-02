import type { CareerFlowApi } from '../../preload/index';

declare global {
  interface Window {
    careerflow: CareerFlowApi;
  }
}

export {};
