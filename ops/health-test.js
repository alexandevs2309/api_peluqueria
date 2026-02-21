import http from 'k6/http';
import { check } from 'k6';

export default function () {
  const res = http.get(__ENV.BASE_URL + '/api/healthz/');
  
  console.log("STATUS:", res.status);
  console.log("BODY:", res.body);

  check(res, {
    'status 200': (r) => r.status === 200,
  });
}
