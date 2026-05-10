import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
    plugins: [
        vue(),
        react(),
    ],
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
            '@pages': resolve(__dirname, 'src/pages'),
            '@components': resolve(__dirname, 'src/components'),
            '@vue-pages': resolve(__dirname, 'src/vue'),
            '@react-pages': resolve(__dirname, 'src/react'),
            '@shared': resolve(__dirname, 'src/shared'),
        },
        dedupe: ['vue', 'vue-demi'],
    },
    optimizeDeps: {
        include: ['vue', 'vue-router', 'pinia'],
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
                    vue: ['vue', 'vue-router', 'pinia'],
                    react: ['react', 'react-dom', 'react-router-dom', 'zustand'],
                },
            },
        },
    },
});
