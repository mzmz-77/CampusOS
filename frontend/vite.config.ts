import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig(({mode})=>({define:{'import.meta.env.VITE_HOSTED_PREVIEW':JSON.stringify(mode==='hosted-preview'?'true':'false')},plugins:[react()],server:{proxy:{'/api':'http://127.0.0.1:8000'}},test:{environment:'jsdom',setupFiles:['./src/test-setup.ts']}}));
