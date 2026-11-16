import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const cssFiles=['prototypes/phase03/style.css','prototypes/phase03/management.css'];
const luminance=hex=>{
 const rgb=[0,2,4].map(i=>parseInt(hex.slice(1+i,3+i),16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
 return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;
};
const contrast=(a,b)=>{const l=[luminance(a),luminance(b)].sort((x,y)=>y-x);return(l[0]+.05)/(l[1]+.05);};
for(const path of cssFiles){
 const css=readFileSync(path,'utf8'),tokens={};
 for(const m of css.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g))tokens[m[1]]=m[2];
 for(const k of ['ink','muted','paper','surface','accent'])assert(tokens[k],path+': missing '+k);
 for(const [label,fg,bg,threshold] of [
  ['body text',tokens.ink,tokens.paper,4.5],
  ['supporting text',tokens.muted,tokens.surface,4.5],
  ['primary action',tokens.accent,'#ffffff',4.5],
  ['navigation selected',tokens.accent,'#ffffff',4.5]
 ]){
  const ratio=contrast(fg,bg);
  assert(ratio>=threshold,path+': '+label+' contrast '+ratio.toFixed(2)+' below '+threshold);
  process.stdout.write(path+' | '+label+' '+ratio.toFixed(2)+':1 PASS\n');
 }
}
