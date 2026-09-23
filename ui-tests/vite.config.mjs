import frontendConfig from '../../petify-frontend/vite.config.ts'

const target = process.env.PETIFY_UI_PROXY_TARGET

export default {
  ...frontendConfig,
  server: {
    ...frontendConfig.server,
    proxy: {
      '/api': { target, changeOrigin: true },
      '/uploads': { target, changeOrigin: true },
    },
  },
}
