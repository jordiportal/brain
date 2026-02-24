// Environment configuration for production
// These values can be overridden at build time using environment variables
export const environment = {
  production: true,
  apiUrl: (typeof window !== 'undefined' && (window as any)['env']?.['apiUrl']) || '/api/v1',
  ollamaDefaultUrl: (typeof window !== 'undefined' && (window as any)['env']?.['ollamaDefaultUrl']) || 'http://localhost:11434',
};
