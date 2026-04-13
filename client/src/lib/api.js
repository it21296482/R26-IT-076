import axios from "axios";

const normalizeApiBaseUrl = () => {
  const configuredUrl = import.meta.env.VITE_API_URL;

  if (!configuredUrl || typeof window === "undefined") {
    return configuredUrl || "/api";
  }

  try {
    const url = new URL(configuredUrl);
    const currentHost = window.location.hostname;
    const isLoopbackPair =
      (url.hostname === "127.0.0.1" && currentHost === "localhost") ||
      (url.hostname === "localhost" && currentHost === "127.0.0.1");

    // Keep client and API on the same local hostname so auth cookies remain first-party in development.
    if (isLoopbackPair) {
      url.hostname = currentHost;
    }

    return url.toString();
  } catch {
    return configuredUrl;
  }
};

const api = axios.create({
  baseURL: normalizeApiBaseUrl(),
  withCredentials: true,
});

export default api;
