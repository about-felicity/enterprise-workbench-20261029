const assert=require('node:assert/strict');
const host={children:[],replaceChildren(){this.children=[]},append(x){this.children.push(x)}};
const $=()=>host,API='/api/geo-creation/';
const document={createElement(tag){return {tag,style:{}}}};
function renderArticlePreview(text,kind){
 const host=$('previewText');host.replaceChildren();
 if(kind!=='markdown'){host.textContent=text;return;}
 for(const line of text.split('\n')){
  const image=line.match(/^!\[产品图片\]\(\/api\/geo-creation\/product_image\?id=(image-[a-f0-9]{32})\)$/);
  if(image){const img=document.createElement('img');img.src=API+'product_image?id='+image[1];img.alt='产品图片';img.style.cssText='display:block;max-width:min(100%,530px);max-height:340px;width:auto;height:auto;object-fit:contain;margin:16px auto';host.append(img);continue;}
  if(!line.trim())continue;
  const heading=line.match(/^(#{1,6})\s+(.*)$/);const node=document.createElement(heading?'h'+Math.min(heading[1].length+1,6):'p');
  node.textContent=(heading?heading[2]:line).replace(/\*\*([^*]+)\*\*/g,'$1');host.append(node);
 }
}


renderArticlePreview('## 产品\n![产品图片](/api/geo-creation/product_image?id=image-11111111111111111111111111111111)\n<script>alert(1)</script>','markdown');
assert.equal(host.children[1].tag,'img');assert.equal(host.children[1].src,API+'product_image?id=image-11111111111111111111111111111111');
assert.equal(host.children[2].textContent,'<script>alert(1)</script>');
assert.match(host.children[1].style.cssText,/object-fit:contain/);
console.log('Preview image routing, sizing and text escaping passed');
