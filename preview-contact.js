/* PREVIEW ONLY: contact cards, Add New, and right-column height. Nothing here is saved to the database. */
(function(){
 if(window.__pc)return;window.__pc=1;
 var $=function(i){return document.getElementById(i)};
 var cust=$("cust");if(!cust)return;
 var cc=cust.closest(".card"),w=cust.parentNode;
 var st=document.createElement("style");
 st.textContent="#cust td:first-child{cursor:pointer;color:#1c4fd6;text-decoration:underline}"+
  "#pcBack{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:50000;display:none;align-items:center;justify-content:center;padding:12px}"+
  "#pcBox{background:#fff8e8;border-radius:14px;padding:16px;width:min(460px,96vw);max-height:92vh;overflow:auto;font-size:16px}"+
  "#pcBox label{display:block;font-size:14px;margin-top:8px}#pcBox input,#pcBox select,#pcBox textarea{width:100%;font-size:16px;padding:8px;box-sizing:border-box;border:2px solid #222;border-radius:8px;background:#fff}"+
  "#pcBox .two{display:flex;gap:8px}#pcBox .two>label{flex:1}"+
  "#pcBox .bad{outline:3px solid #c0392b}#pcBox button{font-size:16px;padding:10px 14px;border:2px solid #222;border-radius:8px;background:#fff}"+
  "#pcBox button.pri{background:#2f6bff;color:#fff}#pcAdd{float:right;font-size:14px;padding:4px 10px;border:2px solid #222;border-radius:8px;background:#fff}";
 document.head.appendChild(st);
 /* ---- right column ends level with the left column ---- */
 try{Object.defineProperty(cc,"offsetParent",{get:function(){return null}})}catch(e){}
 var main=document.querySelector("main"),left=main.querySelector("section"),right=main.querySelector("aside");
 function lastVis(el){var k=el.children;for(var i=k.length-1;i>=0;i--){var r=k[i].getBoundingClientRect();if(r.height>0&&getComputedStyle(k[i]).display!=="none")return k[i]}return null}
 function sync(){if(!cc.getClientRects().length)return;if(window.innerWidth<=900){w.style.maxHeight="360px";return}
  var a=lastVis(right),l=lastVis(left);if(!a||!l)return;
  var d=a.getBoundingClientRect().bottom-l.getBoundingClientRect().bottom;if(Math.abs(d)<3)return;
  w.style.maxHeight=Math.max(120,w.offsetHeight-d)+"px"}
 setInterval(sync,700);window.addEventListener("resize",sync);setTimeout(sync,300);
 /* ---- contact card ---- */
 var back=document.createElement("div");back.id="pcBack";back.innerHTML='<div id="pcBox"></div>';document.body.appendChild(back);
 var box=$("pcBox");
 function esc(s){return String(s==null?"":s).split("&").join("&amp;").split("<").join("&lt;").split('"').join("&quot;")}
 function split(n){n=(n||"").trim();var i=n.lastIndexOf(" ");return i<0?[n,""]:[n.slice(0,i),n.slice(i+1)]}
 function lf(n){var p=split(n);return p[1]?p[1]+", "+p[0]:p[0]}
 function findCust(r){var tds=r.querySelectorAll("td");if(tds.length<2)return null;var nm=tds[0].textContent.trim(),tx=tds[1].textContent;var all=Object.values(S.cust);
  for(var i=0;i<all.length;i++){if(lf(all[i].name)===nm&&tx.indexOf(all[i].email)>=0)return all[i]}return null}
 function orders(c){var k=ck(c),out=[];SHOWS.forEach(function(s,si){var sh=S.shows[si],byO={};Object.keys(sh.seats).forEach(function(id){var x=sh.seats[id];if(x&&x.guest&&ck(x.guest)===k){var o=x.order||"-";(byO[o]=byO[o]||[]).push(id)}});
   Object.keys(byO).forEach(function(o){out.push(fmt(s[0])+" - "+s[1]+": Order "+o+" (seats "+byO[o].join(", ")+")")})});return out}
 var HOW=["Google","Newspaper","Poster","Friends","White Sheets","Radio"];
 function open(c){
  var isNew=!c,p=isNew?["",""]:split(c.name),key=isNew?"":("pc_notes_"+c.email.toLowerCase()),notes=isNew?"":(localStorage.getItem(key)||"");
  var ords=isNew?[]:orders(c);
  box.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center"><h3 style="margin:0">'+(isNew?"New contact":"Contact card")+'</h3><button id="pcX">Close</button></div>'+
   '<div style="font-size:12px;color:#8a5a00;margin-top:4px">PREVIEW: nothing here is saved to the real customer list yet.</div>'+
   '<div class="two"><label>First name *<input id="pcF" value="'+esc(p[0])+'"></label><label>Last name *<input id="pcL" value="'+esc(p[1])+'"></label></div>'+
   '<label>Phone *<input id="pcP" type="tel" value="'+esc(isNew?"":fmtPh(c.phone))+'"></label>'+
   '<label>Email *<input id="pcE" type="email" value="'+esc(isNew?"":c.email)+'"></label>'+
   '<label>Street address<input id="pcA"></label>'+
   '<div class="two"><label>City<input id="pcC" value="'+esc(isNew?"":(c.where||""))+'"></label><label style="flex:0 0 70px">State<input id="pcS"></label><label style="flex:0 0 90px">ZIP<input id="pcZ"></label></div>'+
   '<label>How did they hear about us?<select id="pcH"><option value="">Choose one...</option>'+HOW.map(function(h){return '<option'+((!isNew&&c.how===h)?" selected":"")+'>'+h+'</option>'}).join("")+'</select></label>'+
   '<div style="margin-top:12px;font-weight:bold">Shows and orders</div>'+
   '<div style="font-size:14px">'+(ords.length?ords.map(function(o){return "<div>"+esc(o)+"</div>"}).join(""):'<span style="color:#777">'+(isNew?"None yet. Shows and orders fill in when they buy seats.":"No seats on file.")+"</span>")+'</div>'+
   '<label>Notes (admin only: Debbie / Clint, door never sees this)<textarea id="pcN" rows="4" placeholder="Anything worth remembering about this guest...">'+esc(notes)+'</textarea></label>'+
   '<div id="pcM" style="color:#c0392b;min-height:20px;font-size:14px;margin-top:6px"></div>'+
   '<div style="display:flex;gap:8px;margin-top:6px"><button class="pri" id="pcSave">'+(isNew?"Add contact":"Save")+'</button><button id="pcCancel">Cancel</button></div>';
  back.style.display="flex";
  function close(){back.style.display="none"}
  $("pcX").onclick=close;$("pcCancel").onclick=close;
  $("pcSave").onclick=function(){
   var f=$("pcF"),l=$("pcL"),ph=$("pcP"),em=$("pcE"),bad=[];
   [f,l,ph,em].forEach(function(e){e.classList.remove("bad")});
   if(!f.value.trim()){bad.push(f);}
   if(!l.value.trim()){bad.push(l);}
   if(ph.value.split("").filter(function(ch){return ch>="0"&&ch<="9"}).length<10){bad.push(ph)}
   var ev=em.value.trim(),at=ev.indexOf("@");if(at<1||ev.indexOf(".",at)<at+2||ev.indexOf(" ")>=0){bad.push(em)}
   if(bad.length){bad.forEach(function(e){e.classList.add("bad")});$("pcM").textContent="First name, last name, a full phone number and an email are required.";return}
   var nm=f.value.trim()+" "+l.value.trim();
   if(isNew){var g={name:nm,phone:ph.value.trim(),email:ev,how:$("pcH").value,where:$("pcC").value.trim()};
    var k=ck(g);if(S.cust[k]){$("pcM").textContent="That name and email are already in the customer list.";return}
    S.cust[k]={name:nm,phone:g.phone,email:ev,how:g.how,where:g.where,shows:{},ed:Date.now()};
    var nv=$("pcN").value;if(nv)localStorage.setItem("pc_notes_"+ev.toLowerCase(),nv);
    renderCust();toast("Preview only - "+nm+" added on screen, not saved to the database")}
   else{localStorage.setItem(key,$("pcN").value);toast("Preview only - notes kept on this device, not in the database")}
   close()};
 }
 back.onclick=function(e){if(e.target===back)back.style.display="none"};
 cust.addEventListener("click",function(e){var r=e.target.closest&&e.target.closest("tr");if(!r)return;var c=findCust(r);if(c)open(c)});
 var h3=cc.querySelector("h3");if(h3){var ab=document.createElement("button");ab.id="pcAdd";ab.type="button";ab.textContent="Add New";ab.onclick=function(){open(null)};h3.appendChild(ab)}
})();
