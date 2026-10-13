(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const data = window.SCHEDULE_DATA;
  const days = ['一','二','三','四','五','六','日'];
  const periodTimes = data.periodTimes;
  const icons = {
    book:'<path d="M3 5h6l3 2 3-2h6v15h-6l-3 2-3-2H3zM12 7v15"/>',
    calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 11h18m-13 4h2m4 0h2m-8 3h2"/>',
    grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    settings:'<path d="m9 3-.6 2.4-2.1 1.2L4 6l-2 3.5 1.7 1.8v2.4L2 15.5 4 19l2.3-.6 2.1 1.2L9 22h4l.6-2.4 2.1-1.2 2.3.6 2-3.5-1.7-1.8v-2.4L20 9.5 18 6l-2.3.6-2.1-1.2L13 3z"/><circle cx="11" cy="12.5" r="3"/>',
    external:'<path d="M14 3h7v7M21 3l-10 10M10 5H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/>',
    download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4"/>',
    pin:'<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    left:'<path d="m14 6-6 6 6 6"/>',right:'<path d="m9 6 6 6-6 6"/>',
    list:'<path d="M9 5h12M9 12h12M9 19h12M3 5h1M3 12h1M3 19h1"/>',
    info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
    search:'<circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/>',
    close:'<path d="m6 6 12 12M6 18 18 6"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    user:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    leaf:'<path d="M20 3C11 1 3 6 3 13a7 7 0 0 0 14 0c0-4 1-7 3-10ZM4 21 14 9"/>'
  };
  function icon(name){ return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.book}</svg>`; }
  function hydrateIcons(root=document){root.querySelectorAll('[data-icon]').forEach(e=>e.innerHTML=icon(e.dataset.icon));}
  const esc = text => String(text).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function read(key,fallback){try{return JSON.parse(localStorage.getItem(key))??fallback;}catch{return fallback;}}
  let settings = read('kejian.settings.v1',{});
  if(!settings || typeof settings!=='object') settings={};
  // Migrate the previously unconfirmed calendar once, retaining notes and appearance.
  if(settings.calendarVersion!==data.calendarVersion){settings.start=data.semesterStart;settings.calendarVersion=data.calendarVersion;}
  if(!/^\d{4}-\d{2}-\d{2}$/.test(settings.start||'') || new Date(settings.start+'T00:00:00Z').getUTCDay()!==1) settings.start=data.semesterStart;
  settings.opacity=Math.max(65,Math.min(100,Number(settings.opacity)||88));
  let notes=read('kejian.notes.v1',{}); if(!notes||typeof notes!=='object') notes={};
  function persist(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{toast('浏览器未允许保存，设置仅在本次打开生效');return false;}}
  function today(){const p=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());const get=t=>p.find(x=>x.type===t).value;return new Date(`${get('year')}-${get('month')}-${get('day')}T00:00:00Z`);}
  function currentWeek(){return settings.start?Math.floor((today()-new Date(settings.start+'T00:00:00Z'))/604800000)+1:null;}
  const clampWeek=n=>Math.min(20,Math.max(1,n));
  let week=clampWeek(currentWeek()??6), day=today().getUTCDay()||7;
  let view='week';
  let weekends=!!settings.weekends;
  if(day>5) weekends=true;
  let selectedCourse=null;
  const names=[...new Set(data.courses.map(c=>c.name))];
  const palettes=[['#e4edf0','#8ba8b4','#3d5e6b'],['#eaece2','#a8af8d','#626c48'],['#dfeceb','#86aaa3','#3d665f'],['#e8e6f0','#a59eba','#625b7b'],['#efe9df','#b8a68b','#7a6950'],['#e4eaf1','#8ba2ba','#4d647d'],['#eee6e6','#bba1a1','#7f6060'],['#e9e9df','#acac88','#73734f']];
  function color(c){const p=palettes[names.indexOf(c.name)%palettes.length];return `--course-bg:${p[0]};--course-accent:${p[1]};--course-fg:${p[2]}`;}
  function activeCourses(){return data.courses.filter(c=>c.weekStart<=week && c.weekEnd>=week).sort((a,b)=>a.day-b.day||a.start-b.start);}
  function recurrence(c){return c.weekStart===c.weekEnd?`第 ${c.weekStart} 周`:`第 ${c.weekStart}–${c.weekEnd} 周`;}
  function period(c){return `第 ${c.start}–${c.end} 节`;}
  function time(c){return `${periodTimes[c.start-1][0]}–${periodTimes[c.end-1][1]}`;}
  function room(c){return c.location.replace('从化校区 ','');}
  function dateForDay(d){if(!settings.start)return null;return new Date(new Date(settings.start+'T00:00:00Z').getTime()+((week-1)*7+d-1)*86400000);}
  const dateText=d=>`${String(d.getUTCMonth()+1).padStart(2,'0')}.${String(d.getUTCDate()).padStart(2,'0')}`;
  function isToday(d){return dateForDay(d)?.getTime()===today().getTime();}
  function card(c,grid=false){return `<button class="course-card ${c.end-c.start<2?'compact':''}" data-course="${c.id}" style="${color(c)}${grid?`;grid-column:${c.day+1};grid-row:${c.start+1} / span ${c.end-c.start+1}`:''}" aria-label="${esc(c.name)}，星期${days[c.day-1]}，${period(c)}，${esc(room(c))}"><strong>${esc(c.name)}</strong><span class="room">${esc(room(c))}</span><span class="teacher">${esc(c.teacher)}</span><span class="period">${period(c)}</span></button>`;}
  function render(){
    const courses=activeCourses();
    $('week-select').value=week;
    $('prev-week').disabled=week===1;$('next-week').disabled=week===20;
    $('class-count').textContent=courses.length;$('period-count').textContent=courses.reduce((s,c)=>s+c.end-c.start+1,0);
    const busyDays=new Set(courses.map(c=>c.day)).size;
    $('week-message').textContent=courses.length?'张弛有度，按自己的节奏来。':'这一周，课表里没有安排。';
    $('week-meta').textContent=courses.length?`${busyDays} 天有课 · ${new Set(courses.map(c=>c.name)).size} 门课程 · 按第 ${week} 周安排`:'原始课表未列出本周课程，请留意班级通知';
    $('calendar-caption').textContent=settings.start?`${dateText(dateForDay(1))} — ${dateText(dateForDay(7))} · ${dateForDay(1).getUTCFullYear()} 年${currentWeek()===week?' · 本周':''}`:`未设置校历 · 当前展示第 ${week} 周`;
    $('calendar-setup').textContent=settings.start?'调整校历 ↗':'设置校历 ↗';
    const hasWeekendCourses=courses.some(c=>c.day>5);
    $('weekend-toggle').checked=weekends||hasWeekendCourses;
    $('weekend-toggle').disabled=hasWeekendCourses;
    $('weekend-label').textContent=hasWeekendCourses?'本周有课 · 显示周末':'显示周末';
    const count=weekends||hasWeekendCourses?7:5;
    const first=dateForDay(1), last=dateForDay(7);
    const calendarNotes=data.calendarNotes.filter(n=>first&&last&&new Date(n.start+'T00:00:00Z')<=last&&new Date(n.end+'T00:00:00Z')>=first);
    $('calendar-notes').hidden=!calendarNotes.length;
    $('calendar-notes').textContent=calendarNotes.map(n=>n.text).join(' ');
    let html='<div class="grid-corner" style="grid-column:1;grid-row:1">节次 / 时间</div>';
    for(let d=1;d<=count;d++) html+=`<div class="day-header ${isToday(d)?'today':''}" style="grid-column:${d+1};grid-row:1">周${days[d-1]}<span>${dateForDay(d)?dateText(dateForDay(d)):['MON','TUE','WED','THU','FRI','SAT','SUN'][d-1]}</span></div>`;
    for(let p=0;p<periodTimes.length;p++){
      html+=`<div class="time-label" style="grid-row:${p+2}" aria-label="第 ${p+1} 节，${periodTimes[p][0]} 至 ${periodTimes[p][1]}"><b>${p+1}</b><span>${periodTimes[p][0]}</span><span>${periodTimes[p][1]}</span></div>`;
      for(let d=1;d<=count;d++)html+=`<div class="grid-cell ${isToday(d)?'current':''}" style="grid-column:${d+1};grid-row:${p+2}"></div>`;
    }
    html+=courses.filter(c=>c.day<=count).map(c=>card(c,true)).join('');
    $('week-grid').style.setProperty('--days',count);$('week-grid').innerHTML=html;
    if(day>count)day=1;
    $('day-tabs').innerHTML=Array.from({length:count},(_,i)=>`<button class="${day===i+1?'active':''}" data-day="${i+1}" aria-pressed="${day===i+1}">周${days[i]}<small>${dateForDay(i+1)?dateText(dateForDay(i+1)):courses.filter(c=>c.day===i+1).length+' 次课'}</small></button>`).join('');
    const daily=courses.filter(c=>c.day===day);
    $('day-list').innerHTML=daily.length?daily.map(c=>`<div class="daily-row"><div class="daily-time">${time(c)}<small>${period(c)}</small></div>${card(c)}</div>`).join(''):`<div class="empty-state">${icon('leaf')}<h3>这一天，留一点空白。</h3><p>第 ${week} 周 · 周${days[day-1]}暂无课程安排</p></div>`;
    $('week-grid').hidden=view!=='week';$('day-container').hidden=view!=='day';
    $('week-view').setAttribute('aria-pressed',view==='week');$('day-view').setAttribute('aria-pressed',view==='day');
  }
  function renderCatalog(){const q=$('course-search').value.trim().toLowerCase();const filtered=names.filter(n=>data.courses.some(c=>c.name===n&&[c.name,c.teacher,c.location].some(v=>v.toLowerCase().includes(q))));$('all-courses').innerHTML=filtered.length?filtered.map(n=>{const courses=data.courses.filter(c=>c.name===n);return `<article class="catalog-card" style="${color(courses[0])}"><i></i><h3>${esc(n)}</h3><p>${esc(courses[0].teacher)} · ${esc(room(courses[0]))}</p>${courses.map(c=>`<button class="catalog-session" data-course="${c.id}"><span>周${days[c.day-1]} · ${period(c)}<br>${time(c)}</span><span>${recurrence(c)} ↗</span></button>`).join('')}</article>`;}).join(''):'<div class="empty-state"><h3>没有找到匹配的课程</h3><p>试试课程名称、老师姓名或教室。</p></div>';}
  function openCourse(id){const c=data.courses.find(c=>c.id===id);if(!c)return;selectedCourse=c;$('course-title').textContent=c.name;const rows=[['clock','上课时间',`星期${days[c.day-1]} · ${period(c)}<br>${time(c)}`],['calendar','上课周次',recurrence(c)],['pin','上课地点',esc(c.location)],['user','授课教师',esc(c.teacher)]];if(c.courseType)rows.push(['book','课程类型',esc(c.courseType)]);if(c.credits)rows.push(['book','学分',esc(c.credits)]);$('course-details').innerHTML=rows.map(([i,label,value])=>`<div class="detail-row">${icon(i)}<span>${label}</span><b>${value}</b></div>`).join('');$('course-note').value=typeof notes[c.name]==='string'?notes[c.name]:'';$('course-dialog').showModal();}
  function openSettings(){ $('semester-start').value=settings.start||'';$('opacity').value=settings.opacity;$('opacity-value').value=`${settings.opacity}%`;$('settings-error').textContent='';$('settings-dialog').showModal(); }
  function toast(message){$('toast').textContent=message;$('toast').classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').classList.remove('show'),3200);}
  $('week-select').innerHTML=Array.from({length:20},(_,i)=>`<option value="${i+1}">第 ${i+1} 周</option>`).join('');
  $('time-reference').innerHTML=periodTimes.map((b,i)=>`<div><span>第 ${i+1} 节</span><b>${b[0]}–${b[1]}</b></div>`).join('');
  document.querySelector('.nav-count').textContent=names.length;
  $('catalog-count').textContent=`${names.length} 门`;
  $('today-date').textContent=new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'long',day:'numeric',weekday:'long'}).format(new Date());
  document.documentElement.style.setProperty('--panel-opacity',settings.opacity/100);
  $('prev-week').onclick=()=>{week--;render();};$('next-week').onclick=()=>{week++;render();};
  $('week-select').onchange=e=>{week=Number(e.target.value);render();};
  $('week-view').onclick=()=>{view='week';render();};$('day-view').onclick=()=>{view='day';render();};
  $('current-week').onclick=()=>{const current=currentWeek();if(current===null){openSettings();toast('先设置第 1 周的星期一，即可定位本周');return;}week=clampWeek(current);day=today().getUTCDay()||7;if(day>5)weekends=true;render();if(current<1||current>20)toast('当前日期不在本学期第 1–20 周内，已定位到学期边界');};
  $('weekend-toggle').onchange=e=>{weekends=e.target.checked;settings.weekends=weekends;persist('kejian.settings.v1',settings);render();};
  document.addEventListener('click',e=>{const c=e.target.closest('[data-course]');if(c)openCourse(c.dataset.course);const d=e.target.closest('[data-day]');if(d){day=Number(d.dataset.day);render();}});
  document.querySelectorAll('[data-page]').forEach(button=>button.onclick=()=>{const isSchedule=button.dataset.page==='schedule';$('schedule-page').hidden=!isSchedule;$('courses-page').hidden=isSchedule;$('page-label').textContent=isSchedule?'我的课表':'全部课程';$('page-title').innerHTML=isSchedule?'每一课，都心中有数<span>。</span>':'学期里的每一份收获<span>。</span>';document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b===button));if(!isSchedule)renderCatalog();});
  $('course-search').oninput=renderCatalog;
  ['settings-nav','settings-top','calendar-setup'].forEach(id=>$(id).onclick=openSettings);
  document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>b.closest('dialog').close());
  document.querySelectorAll('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}}));
  $('save-note').onclick=()=>{notes[selectedCourse.name]=$('course-note').value;const saved=persist('kejian.notes.v1',notes);$('course-dialog').close();if(saved)toast('课程备忘已保存');};
  $('opacity').oninput=e=>{$('opacity-value').value=`${e.target.value}%`;document.documentElement.style.setProperty('--panel-opacity',e.target.value/100);};
  $('settings-dialog').addEventListener('close',()=>document.documentElement.style.setProperty('--panel-opacity',settings.opacity/100));
  $('settings-form').onsubmit=e=>{e.preventDefault();const start=$('semester-start').value;if(start&&new Date(start+'T00:00:00Z').getUTCDay()!==1){$('settings-error').textContent='请选择星期一，作为第 1 教学周的开始日期。';return;}settings.start=start||data.semesterStart;settings.opacity=Number($('opacity').value);const saved=persist('kejian.settings.v1',settings);week=clampWeek(currentWeek());render();$('settings-dialog').close();if(saved)toast('课表设置已保存');};
  document.querySelector('.brand').onclick=()=>document.querySelector('[data-page="schedule"]').click();
  hydrateIcons();render();
})();
