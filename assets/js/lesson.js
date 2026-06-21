/* Shared behavior for MCC tutoring lesson kits */
function say(t){ try{ window.speechSynthesis.cancel(); var u=new SpeechSynthesisUtterance(t); u.lang='en-US'; u.rate=0.9; window.speechSynthesis.speak(u);}catch(e){} }
(function(){
  var d=document.getElementById('yr'); if(d) d.textContent=(new Date()).getFullYear();
  var nav=document.querySelector('.hb-nav');
  if(nav){
    var links=[].slice.call(nav.querySelectorAll('a'));
    var secs=links.map(function(a){return document.getElementById(a.getAttribute('href').slice(1));});
    var onScroll=function(){ var y=window.scrollY+170,cur=0; for(var i=0;i<secs.length;i++){ if(secs[i]&&secs[i].offsetTop<=y) cur=i; } links.forEach(function(a,i){a.classList.toggle('active',i===cur);}); };
    window.addEventListener('scroll',onScroll,{passive:true}); onScroll();
  }
  var top=document.querySelector('.to-top');
  if(top){ top.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});}); window.addEventListener('scroll',function(){top.classList.toggle('show',window.scrollY>600);},{passive:true}); }
})();
