import {spawnSync} from 'node:child_process';
import {cpSync,mkdirSync,rmSync} from 'node:fs';
const result=spawnSync(process.platform==='win32'?'npm.cmd':'npm',['run','build:experience'],{cwd:new URL('../frontend',import.meta.url),stdio:'inherit'});
if(result.status!==0)process.exit(result.status||1);
const target=new URL('../dist',import.meta.url);rmSync(target,{recursive:true,force:true});mkdirSync(target,{recursive:true});cpSync(new URL('../frontend/dist',import.meta.url),target,{recursive:true});
