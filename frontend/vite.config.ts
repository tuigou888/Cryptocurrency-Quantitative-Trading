import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
    plugins: [
        vue(),
    ],
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
            '@pages': resolve(__dirname, 'src/pages'),
            '@components': resolve(__dirname, 'src/components'),
            '@vue-pages': resolve(__dirname, 'src/vue'),
            '@shared': resolve(__dirname, 'src/shared'),
        },
    },
    optimizeDeps: {
        include: ['vue', 'vue-router', 'echarts'],
        exclude: ['plotly.js'],
    },
    server: {
        port: 3000,
        proxy: {
            '/api': {
                target: 'http://localhost:8501',
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: 'dist',
        rollupOptions: {
            output: {
                manualChunks: {
                    vue: ['vue', 'vue-router'],
                },
            },
        },
    },
});
