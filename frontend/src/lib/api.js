import axios from 'axios';

export const api = axios.create({ baseURL: '/api/v1/', withCredentials: true, timeout: 20000 });
let csrfToken;
let csrfRequest;

export async function refreshCsrf() {
  if (!csrfRequest) {
    csrfRequest = api.get('auth/csrf/').then(({ data }) => {
      csrfToken = data.csrfToken;
      return csrfToken;
    }).finally(() => { csrfRequest = undefined; });
  }
  return csrfRequest;
}

export function clearCsrf() { csrfToken = undefined; }

api.interceptors.request.use(async (config) => {
  const method = (config.method || 'get').toLowerCase();
  if (!['get', 'head', 'options'].includes(method)) {
    config.headers['X-CSRFToken'] = csrfToken || await refreshCsrf();
  }
  return config;
});

export function errorMessage(error) {
  return error.response?.data?.message || (error.response
    ? 'Something went wrong. Please try again.'
    : 'Unable to connect. Check your connection and try again.');
}
