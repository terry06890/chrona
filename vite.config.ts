/// <reference types="vitest" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [vue()],
	base: '/',
	server: {
		proxy: {'/data': 'http://localhost:8000', '/hist_data': 'http://localhost:8000'},
		watch: {
			ignored: ['**/backend', '**/public'],
		},
	},
	build: {
		sourcemap: true,
	},
	test: {
		globals: true,
		environment: 'happy-dom',
	},
})
