import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// ===== MÉTRICAS PERSONALIZADAS =====
const errorRate = new Rate('errors');

// ===== CONFIGURACIÓN PRINCIPAL =====
export const options = {
  scenarios: {
    normal_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 20 },
        { duration: '5m', target: 50 },
        { duration: '2m', target: 0 },
      ],
      gracefulRampDown: '30s',
    },
    peak_load: {
      executor: 'ramping-vus',
      startTime: '10m',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },
        { duration: '3m', target: 100 },
        { duration: '2m', target: 0 },
      ],
      gracefulRampDown: '30s',
    },
  },

  thresholds: {
    http_req_duration: ['p(95)<800'],  // 95% < 800ms
    http_req_failed: ['rate<0.01'],    // <1% errores
    errors: ['rate<0.01'],
  },
};

// ===== VARIABLES DE ENTORNO =====
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TOKENS = (__ENV.API_TOKENS || '').split(',');

// ===== FUNCIÓN AUXILIAR SEGURA =====
function safeJSON(body) {
  try {
    return JSON.parse(body);
  } catch {
    return null;
  }
}

export default function () {

  // Rotar tokens si hay varios (simula múltiples usuarios)
  const token = TOKENS.length > 1
    ? TOKENS[__VU % TOKENS.length]
    : TOKENS[0];

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  const action = Math.random();

  // ===== DISTRIBUCIÓN REALISTA =====
  if (action < 0.25) {
    dashboard(headers);
  } else if (action < 0.50) {
    listSales(headers);
  } else if (action < 0.70) {
    listEmployees(headers);
  } else if (action < 0.90) {
    createSale(headers);
  } else {
    healthCheck();
  }

  sleep(Math.random() * 2 + 1);
}

// ===== ENDPOINTS =====

function healthCheck() {
  const res = http.get(`${BASE_URL}/healthz/`);
  check(res, {
    'healthz 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function dashboard(headers) {
  const res = http.get(`${BASE_URL}/api/pos/dashboard-stats/`, { headers });
  check(res, {
    'dashboard 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function listSales(headers) {
  const res = http.get(`${BASE_URL}/api/pos/sales/?limit=20`, { headers });
  check(res, {
    'sales 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function listEmployees(headers) {
  const res = http.get(`${BASE_URL}/api/employees/`, { headers });
  check(res, {
    'employees 200': (r) => r.status === 200,
  }) || errorRate.add(1);
}

function createSale(headers) {

  const payload = JSON.stringify({
    client_name: `Cliente-${__VU}-${Date.now()}`,
    employee: 1,
    items: [
      {
        service_name: "Corte",
        quantity: 1,
        price: 40,
      }
    ],
    payment_method: "cash",
    total: 40,
  });

  const res = http.post(`${BASE_URL}/api/pos/sales/`, payload, { headers });

  check(res, {
    'create sale 201': (r) => r.status === 201,
  }) || errorRate.add(1);
}
