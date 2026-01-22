// Environment configuration for production
// These values can be overridden at build time using environment variables
export const environment = {
  production: true,
  apiUrl: (typeof window !== 'undefined' && (window as any)['env']?.['apiUrl']) || 'http://192.168.7.103:8000/api/v1',
  strapiUrl: (typeof window !== 'undefined' && (window as any)['env']?.['strapiUrl']) || 'http://192.168.7.103:1337',
  strapiApiUrl: (typeof window !== 'undefined' && (window as any)['env']?.['strapiApiUrl']) || 'http://192.168.7.103:1337/api',
  ollamaDefaultUrl: (typeof window !== 'undefined' && (window as any)['env']?.['ollamaDefaultUrl']) || 'http://192.168.7.103:11434',
};
