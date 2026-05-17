/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DB_SERVICE_URL: string
  readonly VITE_LOAD_BALANCER_URL: string
  // Add more env variables as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

