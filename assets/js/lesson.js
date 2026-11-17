/* Shared behavior for MCC tutoring lesson kits */
// 🔊 buttons play a natural-voice recording (scripts/build_lesson_audio.py);
// phrases without one fall back to the best voice the browser has.
var AUDIO_DIR='/assets/audio/lesson/', clips=null, player=null;
fetch(AUDIO_DIR+'manifest.json').then(function(r){return r.json();}).then(function(m){clips=m;}).catch(function(){clips={};});
function bestVoice(){
  try{
    var vs=window.speechSynthesis.getVoices().filter(function(v){return /^en[-_]US/i.test(v.lang);});
    var prefer=[/natural/i,/online/i,/google/i,/samantha/i,/ava/i,/allison/i];
    for(var i=0;i<prefer.length;i++){ for(var j=0;j<vs.length;j++){ if(prefer[i].test(vs[j].name)) return vs[j]; } }
    return vs[0]||null;
  }catch(e){ return null; }
}
function speak(t){ try{ window.speechSynthesis.cancel(); var u=new SpeechSynthesisUtterance(t); u.lang='en-US'; u.rate=0.9; var v=bestVoice(); if(v) u.voice=v; window.speechSynthesis.speak(u);}catch(e){} }
function say(t){
  try{ window.speechSynthesis.cancel(); }catch(e){}
  if(player){ player.pause(); }
  var f=clips&&clips[t];
  if(!f){ speak(t); return; }
  player=new Audio(AUDIO_DIR+f);
  player.play().catch(function(){ speak(t); });
}
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
