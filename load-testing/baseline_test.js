import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 10,
  duration: "30s",
};

const BASE_URL = __ENV.BASE_URL || "http://host.docker.internal:8000";
const TX = __ENV.TX || "INQ-DEMO-001";

export default function () {
  const res = http.get(`${BASE_URL}/status/${TX}`);

  check(res, {
    "status is 200": (r) => r.status === 200,
    "response has transaction status": (r) => r.json("status") !== undefined,
  });

  sleep(1);
}