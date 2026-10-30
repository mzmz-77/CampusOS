import {readFile,writeFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const assets=(await readdir(new URL('../dist/assets/',import.meta.url))).map(file=>`/assets/${file}`);
const swPath=new URL('../dist/sw.js',import.meta.url);
let sw=await readFile(swPath,'utf8');
const hash=createHash('sha256').update(await readFile(new URL('../dist/index.html',import.meta.url)));
for(const file of assets)hash.update(await readFile(new URL(`../dist${file}`,import.meta.url)));
const buildId=hash.digest('hex').slice(0,12);
sw=sw.replace("const CACHE='campusos-shell-v1';",`const CACHE='campusos-shell-${buildId}';`).replace("cache.addAll(['/','/manifest.webmanifest','/icon.svg','/icon-192.png','/icon-512.png'])",`cache.addAll(${JSON.stringify(['/','/manifest.webmanifest','/icon.svg','/icon-192.png','/icon-512.png',...assets])})`);
for(const file of assets){if(!sw.includes(file))throw new Error(`Missing precached asset: ${file}`);}
await writeFile(swPath,sw);
console.log(`PWA shell ${buildId}: ${assets.length} assets precached; API data excluded.`);
