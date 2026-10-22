import fs from 'fs';
function load(p){const s=fs.readFileSync(p,'utf8');const i=s.indexOf('{'),j=s.lastIndexOf('}');let t=s.slice(i,j+1);try{return JSON.parse(t)}catch(e){const a=s.indexOf('['),b=s.lastIndexOf(']');return JSON.parse(s.slice(a,b+1))}}
const A=load(process.argv[2]),B=load(process.argv[3]);
const flat=x=>{const m={};const walk=o=>{if(Array.isArray(o))o.forEach(walk);else if(o&&typeof o==='object'){if(o.id&&/^a\d_c\d{3}$/.test(o.id))m[o.id]=o;else Object.values(o).forEach(walk)}};walk(x);return m};
const a=flat(A),b=flat(B);
console.log('cues',Object.keys(a).length,Object.keys(b).length);
const diff=[];for(const k of new Set([...Object.keys(a),...Object.keys(b)])){if(JSON.stringify(a[k])!==JSON.stringify(b[k]))diff.push(k+(a[k]&&b[k]?` dur ${a[k].duration}->${b[k].duration}`:' missing'))}
console.log(diff.length, diff.join('\n'));
