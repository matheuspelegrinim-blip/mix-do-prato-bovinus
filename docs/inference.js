/* RandomForest do primeiro experimento, inferência local no navegador. */
(function(global){
'use strict';
let modelPromise;
function coeffs(src,dst){
 const scale=src/dst, filterscale=Math.max(scale,1), support=2*filterscale, all=[];
 const kernel=(x)=>{x=Math.abs(x);if(x<1) return ((1.5*x-2.5)*x*x+1);if(x<2)return (((-0.5*x+2.5)*x-4)*x+2);return 0;};
 for(let n=0;n<dst;n++){
  const center=(n+0.5)*scale;
  let start=Math.max(0,Math.floor(center-support+0.5));
  let end=Math.min(src,Math.floor(center+support+0.5));
  const weights=[];let sum=0;
  for(let x=start;x<end;x++){let w=kernel((x-center+0.5)/filterscale);weights.push(w);sum+=w;}
  all.push({start,weights:weights.map(w=>w/sum)});
 }
 return all;
}
function resizeRgb(src,sw,sh,dw,dh){
 const xc=coeffs(sw,dw), yc=coeffs(sh,dh), temp=new Uint8ClampedArray(dw*sh*3), out=new Uint8ClampedArray(dw*dh*3);
 for(let y=0;y<sh;y++) for(let x=0;x<dw;x++){
  const {start,weights}=xc[x],o=(y*dw+x)*3;
  for(let k=0;k<3;k++){let val=0;for(let i=0;i<weights.length;i++)val+=src[(y*sw+start+i)*3+k]*weights[i];temp[o+k]=Math.floor(val+0.5);}
 }
 for(let y=0;y<dh;y++) for(let x=0;x<dw;x++){
  const {start,weights}=yc[y],o=(y*dw+x)*3;
  for(let k=0;k<3;k++){let val=0;for(let i=0;i<weights.length;i++)val+=temp[((start+i)*dw+x)*3+k]*weights[i];out[o+k]=Math.floor(val+0.5);}
 }
 return out;
}
function buildFeatures(rgb,w,h,mass){
 const small=resizeRgb(rgb,w,h,16,16), im=resizeRgb(rgb,w,h,64,64), result=new Float32Array(817);
 for(let i=0;i<small.length;i++)result[i]=Math.fround(small[i]/255);
 for(let i=0;i<im.length;i+=3){for(let k=0;k<3;k++){const bin=im[i+k]>>4;result[768+k*16+bin]+=1/(4096*16);}}
 result[816]=Math.fround(mass/1000);
 return result;
}
function forest(forest,x){let sum=0;for(const tree of forest){let i=0;while(tree.l[i]!==-1){i=x[tree.f[i]]<=tree.t[i]?tree.l[i]:tree.r[i];}sum+=tree.v[i];}return sum/forest.length;}
function predict(model,x,mass){const score=forest(model.c,x),fraction=Math.max(0,Math.min(1,forest(model.r,x)));return {presenca:score>0.5,pontuacao:score,massa_estimada_g:fraction*mass,fracao:fraction};}
async function loadModel(){if(!modelPromise)modelPromise=fetch('./model.json').then(r=>{if(!r.ok)throw new Error('Não foi possível carregar o modelo.');return r.json();});return modelPromise;}
async function analyzeImage(file,mass){
 mass=Number(mass);if(!Number.isFinite(mass)||mass<=0||mass>10000)throw new Error('Informe o peso entre 0 e 10.000 g.');
 if(!file||file.size>6*1024*1024)throw new Error('Selecione uma imagem de até 6 MB.');
 const bitmap=await createImageBitmap(file); if(bitmap.width*bitmap.height>25000000){bitmap.close();throw new Error('A imagem é grande demais.');}
 const canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(bitmap,0,0);bitmap.close();
 const rgba=ctx.getImageData(0,0,canvas.width,canvas.height).data,rgb=new Uint8Array(canvas.width*canvas.height*3);
 for(let a=0,b=0;a<rgba.length;a+=4){rgb[b++]=rgba[a];rgb[b++]=rgba[a+1];rgb[b++]=rgba[a+2];}
 const x=buildFeatures(rgb,canvas.width,canvas.height,mass);return predict(await loadModel(),x,mass);
}
global.analyzeImage=analyzeImage;
if(typeof module!=='undefined')module.exports={coeffs,resizeRgb,buildFeatures,predict};
})(typeof window!=='undefined'?window:globalThis);
