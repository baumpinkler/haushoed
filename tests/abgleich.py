# Durchlauf: Abgleich nur der Änderungen. Erster Start liest alles, danach nur Geändertes; Änderungen eines
# anderen Geräts, während die App zu war; Löschen als Markierung; ein altes Gerät ohne Zeitstempel (fängt der
# vollständige Abgleich alle 3 Tage); alte Lösch-Markierungen werden aufgeräumt; „Alles neu abgleichen“.
# Aufruf: python3 tests/abgleich.py   (braucht: pip install playwright && playwright install chromium)
import http.server,threading,functools,json,datetime,os,time
HERE=os.path.dirname(os.path.abspath(__file__)); DOCS=os.path.join(HERE,'..','docs')
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',8795),functools.partial(Q,directory=DOCS));threading.Thread(target=s.serve_forever,daemon=True).start()
T=datetime.date.today(); D=lambda n:(T+datetime.timedelta(days=n)).isoformat()
H='households/h1'; NOW=int(time.time()*1000)
seed={H:{'members':['u1','u2'],'inviteCode':'123456','names':{'u1':'Anna','u2':'Max'},'meta':{'v':4,'planDays':7}}}
for i in range(60): seed[H+f'/articles/a{i}']={'id':f'a{i}','name':f'Artikel {i}','cat':'Kühlregal','mode':'count','unit':'Stk','lots':[{'id':f'l{i}','qty':1,'bought':D(-1)}]}
for i in range(20): seed[H+f'/recipes/r{i}']={'id':f'r{i}','name':f'Rezept {i}','servings':2,'ingredients':'1 Zitrone','steps':''}
# Alte Lösch-Markierung (40 Tage) und eine junge (2 Tage)
seed[H+'/recipes/old']={'id':'old','_del':True,'updated':{'__ts':NOW-40*864e5}}
seed[H+'/recipes/young']={'id':'young','_del':True,'updated':{'__ts':NOW-2*864e5}}
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844})
    ctx.route('**/www.gstatic.com/**',lambda r:r.abort()); ctx.route('**/fonts.*/**',lambda r:r.abort())
    ctx.add_init_script("window.FAKE_UID='u1'; window.FAKE_SEED=%s;"%json.dumps(seed)); ctx.add_init_script(path=os.path.join(HERE,'fakefb.js'))
    pg=ctx.new_page(); pg.on('pageerror',lambda e:print('PAGEERR',e))
    def start(tag):
        pg.wait_for_function('R.active===true'); pg.wait_for_timeout(500)
        print(tag, '| Lesezugriffe:', pg.evaluate('FAKE.reads()'), '| Modus:', pg.evaluate("JSON.stringify(R.syncMode)"),
              '| Artikel:', pg.evaluate('Object.keys(S.articles).length'), '| Rezepte:', pg.evaluate('Object.keys(S.recipes).length'))
    def reload(): pg.reload()
    pg.goto('http://127.0.0.1:8795/index.html'); start('1 Erster Start (%d Dokumente)' % len(seed))
    print('1 Lösch-Markierungen im Store: alt', pg.evaluate("FAKE.store.has('households/h1/recipes/old')"), '| jung', pg.evaluate("FAKE.store.has('households/h1/recipes/young')"))
    reload(); start('2 Zweiter Start')
    # 3 Eigene Änderungen: Zeitstempel vom Server, Löschen als Markierung
    pg.evaluate("{const a=clone(S.articles.a1); a.name='Milch'; putArticle(a); delArticle('a2'); remoteUpdate('recipes','r1',{['ratings.u1']:5}); S.recipes.r1={...S.recipes.r1,ratings:{u1:5}};}"); pg.wait_for_timeout(300)
    print('3 im Store: a1', pg.evaluate("JSON.stringify([FAKE.get('households/h1/articles/a1').name, typeof FAKE.ts(FAKE.store.get('households/h1/articles/a1').updated)])"),
          '| a2', pg.evaluate("JSON.stringify(FAKE.store.get('households/h1/articles/a2'))").replace('"__ts":','ts:')[:60],
          '| r1', pg.evaluate("JSON.stringify(Object.keys(FAKE.store.get('households/h1/recipes/r1')))"))
    # 4 Max ändert etwas, während Annas App zu ist
    pg.evaluate("""FAKE.mute=true;
      FAKE.remoteSet('households/h1/articles/neu',{id:'neu',name:'Topfen',cat:'Kühlregal',mode:'count',unit:'Becher',lots:[],updated:HFB.serverTimestamp()});
      FAKE.remoteUpdate('households/h1/articles/a3',{name:'Butter',updated:HFB.serverTimestamp()});
      FAKE.remoteSet('households/h1/recipes/r2',{id:'r2',_del:true,updated:HFB.serverTimestamp()});""")
    pg.evaluate("FAKE.resetReads()"); reload(); start('4 Start nach Max’ Änderungen')
    print('4 sichtbar:', pg.evaluate("JSON.stringify([S.articles.neu&&S.articles.neu.name, S.articles.a3.name, !!S.recipes.r2, !!S.articles.a2, S.articles.a1.name])"))
    # 5 Live: Max ändert, während Annas App offen ist
    pg.evaluate("FAKE.resetReads(); FAKE.remoteUpdate('households/h1/articles/a4',{name:'Joghurt',updated:HFB.serverTimestamp()})"); pg.wait_for_timeout(200)
    print('5 live:', pg.evaluate("S.articles.a4.name"), '| Lesezugriffe dafür:', pg.evaluate('FAKE.reads()'))
    # 6 Altes Gerät schreibt ohne Zeitstempel: der Änderungs-Abgleich sieht das nicht, der vollständige schon
    pg.evaluate("FAKE.mute=true; FAKE.remoteUpdate('households/h1/articles/a5',{name:'Alte Version'})")
    reload(); start('6a Start nach altem Gerät'); print('6a a5:', pg.evaluate("S.articles.a5.name"))
    pg.evaluate("SYNC.full=Date.now()-4*864e5; localStorage.setItem(LS_KEY, JSON.stringify({...S,_sync:SYNC}))")
    pg.evaluate("FAKE.resetReads()"); reload(); start('6b Start nach 4 Tagen'); print('6b a5:', pg.evaluate("S.articles.a5.name"))
    pg.evaluate("FAKE.resetReads()"); reload(); start('6c Start danach')
    # 7 Knopf „Alles neu abgleichen“
    pg.click('[data-tab=more]'); pg.wait_for_timeout(200)
    print('7 Text:', pg.inner_text('#resyncBtn'))
    pg.evaluate("FAKE.resetReads()"); pg.click('#resyncBtn'); pg.wait_for_load_state(); start('7 nach Knopf')
    # 8 Zwischenspeicher weg (z. B. Browserdaten gelöscht): alles lesen, Daten vollständig
    pg.evaluate("localStorage.removeItem('haushoed:cache'); FAKE.resetReads()"); reload(); start('8 ohne Zwischenspeicher')
    b.close()
s.shutdown()
