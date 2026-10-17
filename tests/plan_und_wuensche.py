# Durchlauf: Start mit Firestore-Imitat, Archiv, Tagesansicht eines Gerichts, Wunschliste, Speicher voll.
# Aufruf: python3 tests/plan_und_wuensche.py   (braucht: pip install playwright && playwright install chromium)
import http.server,threading,functools,json,datetime,os
HERE=os.path.dirname(os.path.abspath(__file__)); DOCS=os.path.join(HERE,'..','docs')
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',8799),functools.partial(Q,directory=DOCS));threading.Thread(target=s.serve_forever,daemon=True).start()
T=datetime.date.today(); D=lambda n:(T+datetime.timedelta(days=n)).isoformat()
H='households/h1'
seed={H:{'members':['u1','u2'],'inviteCode':'123456','names':{'u1':'Anna','u2':'Max'},'meta':{'v':4,'planDays':7}},
 H+'/articles/m1':{'id':'m1','name':'Milch','cat':'Kühlregal','loc':'Kühlschrank','mode':'count','unit':'Packung','min':0,'buy':1,'lots':[
   {'id':'a','qty':1,'bought':D(-9),'size':None,'check':None,'expires':D(1)},
   {'id':'b','qty':1,'bought':D(-5),'size':None,'check':D(2),'expires':D(8)}]},
 H+'/articles/f1':{'id':'f1','name':'Mehl','cat':'Trockenware & Konserven','mode':'count','unit':'Packung','base':'g','packSize':1000,'lots':[{'id':'c','qty':1,'bought':D(-20),'size':1000}]},
 H+'/articles/e1':{'id':'e1','name':'Eier','cat':'Kühlregal','mode':'count','unit':'Stk','lots':[{'id':'d','qty':2,'bought':D(-3)}]},
 H+'/recipes/r1':{'id':'r1','name':'Palatschinken','servings':4,'ingredients':'2 Packungen Milch\n500 g Mehl\n4 Eier\n1 Zitrone\nSalz','steps':''},
 H+'/plan/pold1':{'id':'pold1','date':D(-20),'recipeId':'r1','servings':4,'cooked':True},
 H+'/plan/pold2':{'id':'pold2','date':D(-40),'recipeId':'r1','servings':2,'cooked':False},
 H+'/plan/pnew':{'id':'pnew','date':D(3),'recipeId':'r1','servings':4,'cooked':False,'created':1},
 H+'/wishes/r2':{'id':'r2','recipeId':'r2','by':'u2','votes':{'u2':1},'created':1},
 H+'/wishes/r3':{'id':'r3','recipeId':'r3','by':'u2','votes':{'u2':1,'u1':-1},'created':2},
}
for i in range(2,12): seed[H+f'/recipes/r{i}']={'id':f'r{i}','name':f'Gericht {i}','servings':2,'ingredients':'1 Zitrone','steps':''}
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True)
    ctx.route('**/www.gstatic.com/**',lambda r:r.abort()); ctx.route('**/fonts.*/**',lambda r:r.abort())
    ctx.add_init_script("window.FAKE_UID='u1'; window.FAKE_SEED=%s;"%json.dumps(seed)); ctx.add_init_script(path=os.path.join(HERE,'fakefb.js'))
    pg=ctx.new_page(); pg.on('pageerror',lambda e:print('PAGEERR',e)); pg.on('console',lambda m: print('CONSOLE',m.text) if m.type=='error' and 'gstatic' not in m.text and 'Failed to load' not in m.text else None)
    pg.goto('http://127.0.0.1:8799/index.html'); pg.wait_for_function('R.active===true'); pg.wait_for_timeout(500)
    print('1 Lesezugriffe beim Start:', pg.evaluate('FAKE.reads()'), '(Dokumente:', len(seed)-0, ')')
    print('1 Plan lokal:', pg.evaluate('Object.keys(S.plan)'), '| Plan im Store:', pg.evaluate("[...FAKE.store.keys()].filter(k=>k.includes('/plan/'))"))
    print('1 Archiv:', pg.evaluate("JSON.stringify([...FAKE.store.entries()].filter(([k])=>k.includes('/log/')).map(([k,v])=>[k.split('/').pop(), v.meals.map(m=>[m.id,m.n,m.c])]))"))
    print('1 Schreibvorgänge:', pg.evaluate("JSON.stringify(FAKE.writes)"))
    # 2 Tagesansicht
    pg.click('[data-tab=cook]'); pg.wait_for_timeout(300); pg.screenshot(path=os.path.join(HERE,'w1.png'))
    print('2 Plan-Zeile:', pg.inner_text('[data-meal=pnew]').replace('\n',' | '))
    pg.click('[data-meal=pnew]'); pg.wait_for_timeout(300)
    print('2 Gericht:\n  ' + pg.inner_text('.ingprev').replace('\n','\n  ')); print('  Zusammenfassung:', pg.evaluate("document.querySelector('.ingprev').previousElementSibling.innerText"))
    pg.screenshot(path=os.path.join(HERE,'w2.png')); pg.go_back(); pg.wait_for_timeout(300)
    print('2 Einkaufsliste:', pg.evaluate("JSON.stringify(shopList().map(e=>[e.name,e.qty,e.note]))"))
    # 3 Wünsche
    pg.click('[data-cookview=wishes]'); pg.wait_for_timeout(300)
    print('3 Reihenfolge:', pg.evaluate("[...document.querySelectorAll('.wrow')].map(r=>r.innerText.replace(/\\n/g,' '))"))
    pg.click('[data-vote=r3][data-v="1"]'); pg.wait_for_timeout(300)
    print('3 nach Stimme r3:', pg.evaluate("FAKE.get('households/h1/wishes/r3').votes"), '| Schreibart:', pg.evaluate("JSON.stringify(FAKE.writes.filter(w=>w[1].endsWith('wishes/r3')))"))
    pg.click('[data-act=wishadd]'); pg.wait_for_timeout(300)
    print('3 Auswahl ohne r2/r3:', pg.evaluate("[...document.querySelectorAll('[data-wishpick]')].map(b=>b.dataset.wishpick)"))
    pg.click('[data-wishpick=r1]'); pg.wait_for_timeout(300)
    print('3 neuer Wunsch:', pg.evaluate("JSON.stringify(FAKE.get('households/h1/wishes/r1'))"))
    print('3 r2 nochmal:', pg.evaluate("addWish('r2')"), '|', pg.inner_text('#snackMsg'))
    for i in range(4,10): pg.evaluate(f"addWish('r{i}')")
    pg.wait_for_timeout(200); print('3 meine Wünsche:', pg.evaluate('myWishes().length'), '| 8. Wunsch:', pg.evaluate("addWish('r10')"), '|', pg.inner_text('#snackMsg'))
    print('3 Knopf:', pg.inner_text('.actions .hint'), '| disabled', pg.evaluate("document.querySelector('[data-act=wishadd]').disabled"))
    pg.screenshot(path=os.path.join(HERE,'w3.png'), full_page=True)
    # 4 Fremde Stimme kommt rein
    pg.evaluate("FAKE.remoteUpdate('households/h1/wishes/r1', {'votes.u2': -1})"); pg.wait_for_timeout(300)
    print('4 r1 nach Max dagegen:', pg.evaluate("wishScore(S.wishes.r1)"), pg.evaluate("JSON.stringify(S.wishes.r1.votes)"))
    # 5 Einplanen aus der Wunschliste
    pg.click('[data-wish=r2]'); pg.wait_for_timeout(300); pg.screenshot(path=os.path.join(HERE,'w4.png'))
    pg.click('[data-planday="%s"]'%D(5)); pg.wait_for_timeout(400)
    print('5 Wunsch r2 im Store:', pg.evaluate("FAKE.store.has('households/h1/wishes/r2')"), '| Plan:', pg.evaluate("JSON.stringify(Object.values(S.plan).filter(e=>e.recipeId==='r2').map(e=>e.date))"), '|', pg.inner_text('#snackMsg'))
    # 6 Neu laden: kein zweites Aufräumen, Lesezugriffe
    pg.reload(); pg.wait_for_function('R.active===true'); pg.wait_for_timeout(500)
    print('6 nach Reload Lesezugriffe:', pg.evaluate('FAKE.reads()'), '| Schreibvorgänge:', pg.evaluate('FAKE.writes.length'))
    # 7 Speicher voll
    pg.evaluate("""(()=>{const o=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){ if(k==='haushoed:cache' && v.length>window.LIM) { const e=new Error('quota'); e.name='QuotaExceededError'; throw e;} return o.call(this,k,v); };})()""")
    full=pg.evaluate("JSON.stringify(S).length"); nolog=pg.evaluate("JSON.stringify({...S,log:{}}).length"); print('7 Größen', full, nolog)
    pg.evaluate("window.LIM=%d"%((full+nolog)//2)); pg.evaluate("localSave()"); pg.wait_for_timeout(400)
    print('7a Zustand:', pg.evaluate('STORE.state'), '|', pg.inner_text('#snackMsg'))
    pg.evaluate("window.LIM=10"); pg.evaluate("localSave()"); pg.wait_for_timeout(400)
    print('7b Zustand:', pg.evaluate('STORE.state'), '| Cache gelöscht:', pg.evaluate("localStorage.getItem('haushoed:cache')===null"))
    pg.click('[data-tab=more]'); pg.wait_for_timeout(300); print('7c Hinweis:', pg.inner_text('.notice'))
    b.close()
s.shutdown()
