import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:180000,use:{baseURL:process.env.SCRIPTSTUDIO_URL||'http://127.0.0.1:8088',headless:true,viewport:{width:1440,height:1000}},reporter:'list'});
