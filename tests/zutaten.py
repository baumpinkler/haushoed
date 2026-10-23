# Durchlauf: Zutaten im Vorrat zuordnen (mehrere Artikel für eine Zutat), fehlende anlegen, „nicht im Vorrat führen“,
# Rechnung, Einkaufsliste und Kochen mit mehreren Artikeln; Blatt liegt über dem Rezept; Kinder sehen nichts davon.
# Aufruf: python3 tests/zutaten.py   (braucht: pip install playwright && playwright install chromium)
import http.server,threading,functools,json,datetime,os
HERE=os.path.dirname(os.path.abspath(__file__)); DOCS=os.path.join(HERE,'..','docs')
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',8792),functools.partial(Q,directory=DOCS));threading.Thread(target=s.serve_forever,daemon=True).start()
T=datetime.date.today(); D=lambda n:(T+datetime.timedelta(days=n)).isoformat()
H='households/h1'
pasta=lambda i,name,qty:{'id':i,'name':name,'cat':'Nudeln & Reis','loc':'Vorratsschrank','mode':'count','unit':'Pkg','base':'g','packSize':500,'lots':[{'id':i+'1','qty':qty,'bought':D(-5),'size':500}]}
seed={H:{'members':['u1','u2'],'inviteCode':'123456','names':{'u1':'Anna','u2':'Max'},'meta':{'v':4,'planDays':7}},
 H+'/articles/spa':pasta('spa','Spaghetti',1), H+'/articles/pen':pasta('pen','Penne',2),
 H+'/recipes/r1':{'id':'r1','name':'Pasta Pomodoro','servings':4,'ingredients':'800 g Nudeln\n2 Paradeiser\n1 l Wasser\n1 Zitrone','steps':'Kochen.'},
 H+'/plan/p1':{'id':'p1','date':D(1),'recipeId':'r1','servings':4,'cooked':False},
}
def mk(uid, seed_):
    ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True)
    ctx.route('**/www.gstatic.com/**',lambda r:r.abort()); ctx.route('**/fonts.*/**',lambda r:r.abort())
    ctx.add_init_script("window.FAKE_UID='%s'; window.FAKE_SEED=%s;"%(uid,json.dumps(seed_))); ctx.add_init_script(path=os.path.join(HERE,'fakefb.js'))
    pg=ctx.new_page(); pg.on('pageerror',lambda e:print('PAGEERR',e))
    pg.goto('http://127.0.0.1:8792/index.html'); pg.wait_for_function('R.active===true'); pg.wait_for_timeout(400); return pg
with sync_playwright() as p:
    b=p.chromium.launch(); pg=mk('u1', seed)
    st=lambda: pg.evaluate("JSON.stringify(planCalc().status.p1.missing)")
    shop=lambda: pg.evaluate("JSON.stringify(shopList().filter(e=>!e.done).map(e=>[e.name,e.qty]))")
    lines=lambda: pg.eval_on_selector_all('#sheetInner .ingline', 'e=>e.map(x=>x.innerText.replace(/\\n/g," | ").replace(" ›",""))')
    print('1 fehlt:', st(), '| Liste:', shop())
    pg.evaluate("openMeal('p1')"); pg.wait_for_timeout(300)
    print('1 Zeilen:', lines())
    # 2 Nudeln = Penne + Spaghetti
    pg.click('#sheetInner [data-ing="Nudeln"]'); pg.wait_for_timeout(250)
    print('2 Blatt offen:', pg.evaluate("!$('#subInner').hidden"), '| darunter noch das Gericht:', pg.evaluate("!!document.querySelector('#sheetInner #m-cook')"))
    print('2 Vorschläge ohne Suche:', pg.eval_on_selector_all('#sub-hits [data-ladd] .name','e=>e.map(x=>x.innerText)'))
    pg.fill('#f-lq','pen'); pg.wait_for_timeout(100); pg.click('#sub-hits [data-ladd=pen]'); pg.wait_for_timeout(150)
    pg.fill('#f-lq','spa'); pg.wait_for_timeout(100); pg.click('#sub-hits [data-ladd=spa]'); pg.wait_for_timeout(150)
    print('2 zählt dazu:', pg.eval_on_selector_all('#subInner .lot .l','e=>e.map(x=>x.innerText.replace(/\\n/g," | "))'), '| gespeichert:', pg.evaluate("JSON.stringify(S.meta.links)"))
    pg.screenshot(path=os.path.join(HERE,'z1.png'))
    pg.click('#sub-close'); pg.wait_for_timeout(200)
    print('2 fehlt jetzt:', st(), '| Zeile:', [l for l in lines() if 'Nudeln' in l])
    # 3 Paradeiser neu anlegen
    pg.click('#sheetInner [data-ing="Paradeiser"]'); pg.wait_for_timeout(250)
    print('3 Vorschlag Name/Kategorie:', pg.input_value('#f-lnew'), '/', pg.input_value('#f-lcat'))
    pg.click('#sub-create'); pg.wait_for_timeout(200)
    pid=pg.evaluate("findByName('Paradeiser').id")
    print('3 angelegt:', pg.evaluate("JSON.stringify((a=>[a.name,a.cat,a.lots.length])(findByName('Paradeiser')))"), '| Zuordnung:', pg.evaluate("JSON.stringify(S.meta.links.paradeiser)")==json.dumps([pid]), '|', pg.inner_text('#snackMsg'))
    pg.click('#sub-close'); pg.wait_for_timeout(150)
    # 4 Wasser nicht im Vorrat führen; rückgängig und wieder
    pg.click('#sheetInner [data-ing="Wasser"]'); pg.wait_for_timeout(200); pg.click('#sub-none'); pg.wait_for_timeout(150)
    print('4 Wasser:', pg.inner_text('#subInner').split('\n')[2], '| fehlt:', st())
    pg.click('#snackUndo'); pg.wait_for_timeout(150); print('4 rückgängig, fehlt:', st())
    pg.click('#sub-close'); pg.wait_for_timeout(100); pg.click('#sheetInner [data-ing="Wasser"]'); pg.wait_for_timeout(200); pg.click('#sub-none'); pg.wait_for_timeout(150); pg.click('#sub-close'); pg.wait_for_timeout(150)
    print('4 Zeilen:', lines())
    print('4 Einkaufsliste:', shop())
    pg.screenshot(path=os.path.join(HERE,'z2.png'))
    # 5 Kochen: zuerst Penne, dann Spaghetti
    pg.evaluate("cook('p1')"); pg.wait_for_timeout(200)
    g=lambda: pg.evaluate("JSON.stringify([amount(S.articles.pen), amount(S.articles.spa)])")
    print('5 nach Kochen (Penne, Spaghetti in g):', g())
    pg.evaluate("putPlan({id:'p2',date:D2,recipeId:'r1',servings:4,cooked:false,created:2})".replace('D2', json.dumps(D(2)))); pg.wait_for_timeout(150)
    print('5 Gericht 2 braucht 800 g, da sind 700:', pg.evaluate("JSON.stringify(planCalc().status.p2.missing)"), '| Liste:', shop())
    # Reihenfolge: Spaghetti nach vorne → wird nachgekauft
    pg.evaluate("openMeal('p2')"); pg.wait_for_timeout(250); pg.click('#sheetInner [data-ing="Nudeln"]'); pg.wait_for_timeout(200)
    pg.click('#subInner [data-lup=spa]'); pg.wait_for_timeout(150)
    print('5 nach vorne:', pg.evaluate("JSON.stringify(S.meta.links.nudeln)"), '| Liste:', shop())
    pg.click('#sub-close'); pg.wait_for_timeout(150); pg.click('#close'); pg.wait_for_timeout(200)
    # 6 Über dem Rezept: ungespeicherte Änderung bleibt
    pg.evaluate("openRecipe('r1')"); pg.wait_for_timeout(300)
    pg.fill('#r-name','Pasta Pomodoro NEU'); pg.fill('#r-ing','800 g Nudeln\n2 Paradeiser\n1 l Wasser\n1 Zitrone\n1 Bund Basilikum'); pg.wait_for_timeout(400)
    pg.click('#sheetInner [data-ing="Basilikum"]'); pg.wait_for_timeout(200); pg.click('#sub-none'); pg.wait_for_timeout(150); pg.click('#sub-close'); pg.wait_for_timeout(400)
    print('6 Name noch da:', pg.input_value('#r-name'), '| Vorschau Basilikum:', [l for l in lines() if 'Basilikum' in l])
    pg.click('#close'); pg.wait_for_timeout(200)
    # 7 Kinder sehen keine Zuordnung
    seed2=json.loads(json.dumps(seed)); seed2[H]['roles']={'u2':'child'}
    kp=mk('u2', seed2); kp.evaluate("openMeal('p1')"); kp.wait_for_timeout(300)
    print('7 Kind: antippbare Zutaten:', kp.eval_on_selector_all('[data-ing]','e=>e.length'), '| openIngLink:', kp.evaluate("openIngLink('Nudeln'), $('#subInner').hidden"))
    b.close()
s.shutdown()
