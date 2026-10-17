# Durchlauf: Zählart „Nur melden“ (da, wird knapp, aus), Blatt „Verbraucht“ mit Vorschlägen und Kurzbefehle.
# Aufruf: python3 tests/schnell.py   (braucht: pip install playwright && playwright install chromium)
import http.server,threading,functools,json,datetime,os
HERE=os.path.dirname(os.path.abspath(__file__)); DOCS=os.path.join(HERE,'..','docs')
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',8794),functools.partial(Q,directory=DOCS));threading.Thread(target=s.serve_forever,daemon=True).start()
T=datetime.date.today(); D=lambda n:(T+datetime.timedelta(days=n)).isoformat(); M=T.isoformat()[:7]
H='households/h1'
art=lambda i,name,mode,lots,**k:{'id':i,'name':name,'cat':'Kühlregal','loc':'Kühlschrank','mode':mode,'unit':k.pop('unit','Stk'),'min':0,'buy':1,'lots':lots,**k}
seed={H:{'members':['u1'],'inviteCode':'123456','names':{'u1':'Anna'},'meta':{'v':4,'planDays':7}},
 H+'/articles/salz':art('salz','Salz','flag',[{'id':'s1','qty':1,'bought':D(-30)}],cat='Gewürze & Saucen',loc='Vorratsschrank'),
 H+'/articles/milch':art('milch','Milch','count',[{'id':'m1','qty':2,'bought':D(-1),'expires':D(6)}],unit='Packung',openable=True,openMaxDays=3),
 H+'/articles/jog':art('jog','Joghurt','count',[{'id':'j1','qty':4,'bought':D(-2)}],unit='Becher'),
 H+'/articles/sham':art('sham','Shampoo','level',[{'id':'h1','qty':1,'bought':D(-10)}],unit='Flasche',cat='Hygiene',loc='Bad'),
 H+'/articles/kaese':art('kaese','Käse','count',[],unit='Packung'),
 H+'/recipes/r1':{'id':'r1','name':'Nudelwasser','servings':2,'ingredients':'1 TL Salz\n500 ml Wasser','steps':''},
 H+'/plan/p1':{'id':'p1','date':D(1),'recipeId':'r1','servings':2,'cooked':False},
 H+f'/log/{M}':{'id':M,'events':[{'id':f'e{i}','t':'use','a':'jog','n':'Joghurt','q':1,'d':D(-i)} for i in range(5)]+[{'id':'em','t':'use','a':'milch','n':'Milch','q':1,'d':D(-3)}]},
}
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True)
    ctx.route('**/www.gstatic.com/**',lambda r:r.abort()); ctx.route('**/fonts.*/**',lambda r:r.abort())
    ctx.add_init_script("window.FAKE_UID='u1'; window.FAKE_SEED=%s;"%json.dumps(seed)); ctx.add_init_script(path=os.path.join(HERE,'fakefb.js'))
    pg=ctx.new_page(); pg.on('pageerror',lambda e:print('PAGEERR',e))
    pg.goto('http://127.0.0.1:8794/index.html'); pg.wait_for_function('R.active===true'); pg.wait_for_timeout(400)
    row=lambda: pg.inner_text('.row:has([data-flag=salz]), .row:has([data-refill=salz])').replace('\n',' | ')
    onlist=lambda: pg.evaluate("shopList().filter(e=>!e.done).map(e=>e.name).includes('Salz')")
    plan=lambda: pg.evaluate("JSON.stringify(planCalc().status.p1)")
    # 1 Nur melden: Liste, Knopf, Rezepte
    print('1 Zeile:', row(), '| auf der Liste:', onlist(), '| Plan:', plan())
    pg.screenshot(path=os.path.join(HERE,'s1.png'))
    pg.click('[data-flag=salz]'); pg.wait_for_timeout(150)
    print('1 nach Knapp:', row(), '| Liste:', onlist(), '| Plan:', plan(), '|', pg.inner_text('#snackMsg'))
    pg.click('[data-flag=salz]'); pg.wait_for_timeout(150)
    print('1 nach Aus:', row(), '| Liste:', onlist(), '| Plan:', plan(), '| Verlauf:', pg.evaluate("S.log['%s'].events.filter(e=>e.a==='salz').length" % M))
    pg.click('#snackUndo'); pg.wait_for_timeout(150); print('1 rückgängig:', row())
    pg.click('[data-flag=salz]'); pg.wait_for_timeout(100); pg.click('[data-refill=salz]'); pg.wait_for_timeout(150)
    print('1 nach Einräumen:', row(), '| Liste:', onlist())
    pg.evaluate("cook('p1')"); pg.wait_for_timeout(100); print('1 nach Kochen:', pg.evaluate("JSON.stringify([flagState(S.articles.salz), S.articles.salz.lots.length])"))
    # 2 Bearbeiten-Blatt
    pg.click('[data-open=salz]'); pg.wait_for_timeout(300)
    print('2 Blatt:', pg.inner_text('.stockbox').replace('\n',' | '), '| Felder:', [x for x in ['#f-min','#f-openable','#f-buy','#aMinus'] if pg.query_selector(x)])
    pg.click('[data-fstate=low]'); pg.wait_for_timeout(150); print('2 Wird knapp:', pg.evaluate("flagState(S.articles.salz)"))
    pg.click('#f-details summary'); pg.wait_for_timeout(100)
    pg.screenshot(path=os.path.join(HERE,'s2.png'), full_page=True)
    pg.click('#close'); pg.wait_for_timeout(200)
    # 3 Zählart wechseln
    pg.click('[data-open=jog]'); pg.wait_for_timeout(300); pg.click('#f-details summary'); pg.click('[data-mode=flag]'); pg.wait_for_timeout(200)
    print('3 Joghurt → nur melden:', pg.evaluate("JSON.stringify([S.articles.jog.mode, S.articles.jog.lots.map(l=>l.qty), flagState(S.articles.jog)])"))
    pg.click('[data-mode=count]'); pg.wait_for_timeout(200)
    print('3 zurück zu Stück:', pg.evaluate("JSON.stringify([S.articles.jog.mode, S.articles.jog.lots.map(l=>l.qty)])"))
    pg.evaluate("{const a=clone(S.articles.jog); a.lots=[{id:'j1',qty:4,bought:today()}]; putArticle(a);}")
    pg.click('#close'); pg.wait_for_timeout(200)
    # 4 Blatt „Verbraucht“
    pg.click('[data-act=quickuse]'); pg.wait_for_timeout(400)
    print('4 Fokus in der Suche:', pg.evaluate("document.activeElement.id"))
    print('4 Vorschläge:', pg.eval_on_selector_all('#qu-list .qrow', 'e=>e.map(x=>x.innerText.replace(/\\n/g," | "))'))
    pg.screenshot(path=os.path.join(HERE,'s3.png'))
    pg.click('#qu-list [data-quse=jog]'); pg.wait_for_timeout(200)
    print('4 Joghurt −1:', pg.evaluate('total(S.articles.jog)'), '|', pg.inner_text('#snackMsg'), '| Blatt noch offen:', pg.evaluate("!!document.querySelector('#qu-list')"))
    pg.click('#qu-list [data-qopen=milch]'); pg.wait_for_timeout(200)
    print('4 Milch geöffnet:', pg.evaluate("stockText(S.articles.milch)"), '|', pg.inner_text('#snackMsg'))
    pg.fill('#qu-q','sha'); pg.wait_for_timeout(150)
    print('4 Suche „sha“:', pg.eval_on_selector_all('#qu-list .qrow', 'e=>e.map(x=>x.innerText.replace(/\\n/g," | "))'))
    pg.click('#qu-list [data-quse=sham]'); pg.wait_for_timeout(200); print('4 Shampoo:', pg.evaluate("stockText(S.articles.sham)"), '| Fokus:', pg.evaluate("document.activeElement.id||document.activeElement.tagName"))
    pg.fill('#qu-q','kä'); pg.wait_for_timeout(150); print('4 Suche „kä“:', pg.inner_text('#qu-list'))
    pg.fill('#qu-q',''); pg.wait_for_timeout(150)
    print('4 Vorschläge jetzt:', pg.eval_on_selector_all('#qu-list .qrow .l', 'e=>e.map(x=>x.innerText.split("\\n")[0])'))
    pg.click('#close'); pg.wait_for_timeout(200)
    # 5 Kurzbefehle
    pg.goto('http://127.0.0.1:8794/index.html?do=use'); pg.wait_for_timeout(800)
    print('5 ?do=use:', pg.evaluate("!!document.querySelector('#qu-q')"), '| Adresse:', pg.evaluate("location.search||'(leer)'"))
    pg.goto('http://127.0.0.1:8794/index.html?do=scan-use'); pg.wait_for_timeout(900)
    print('5 ?do=scan-use:', pg.evaluate("UI.scanMode"), '| Scanner offen:', pg.evaluate("!!document.querySelector('#cam')"), '| Modus gedrückt:', pg.evaluate("(document.querySelector('[data-smode][aria-pressed=true]')||{}).innerText"))
    m=json.load(open(os.path.join(DOCS,'manifest.webmanifest'),encoding='utf-8')); print('5 Manifest:', [(x['name'],x['url']) for x in m['shortcuts']])
    b.close()
s.shutdown()
