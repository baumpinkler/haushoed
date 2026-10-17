# Durchlauf: EL/TL gegen den Vorrat. Flasche in ml, Pulver in g (Tabelle, Vorschlag, Auswahl), fehlende Packungsgröße, Kochen.
# Aufruf: python3 tests/loeffel.py   (braucht: pip install playwright && playwright install chromium)
import http.server,threading,functools,json,datetime,os
HERE=os.path.dirname(os.path.abspath(__file__)); DOCS=os.path.join(HERE,'..','docs')
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',8798),functools.partial(Q,directory=DOCS));threading.Thread(target=s.serve_forever,daemon=True).start()
T=datetime.date.today(); D=lambda n:(T+datetime.timedelta(days=n)).isoformat()
H='households/h1'
art=lambda i,name,base,lots,mode='count',unit='Glas',**k:{'id':i,'name':name,'cat':'Gewürze & Saucen','loc':'Vorratsschrank','mode':mode,'unit':unit,'base':base,'lots':lots,**k}
seed={H:{'members':['u1'],'inviteCode':'123456','names':{'u1':'Anna'},'meta':{'v':4,'planDays':7}},
 H+'/articles/soja':art('soja','Sojasauce','ml',[{'id':'s1','qty':0.2,'bought':D(-30),'size':250}],mode='level',unit='Flasche',packSize=250),
 H+'/articles/curry':art('curry','Currypulver','g',[{'id':'c1','qty':1,'bought':D(-30),'size':40}],packSize=40),
 H+'/articles/zauber':art('zauber','Zaubergewürz','g',[{'id':'z1','qty':1,'bought':D(-30),'size':50}],packSize=50),
 H+'/articles/kk':art('kk','Kreuzkümmel',None,[{'id':'k1','qty':1,'bought':D(-30)}]),
 H+'/recipes/r1':{'id':'r1','name':'Curry','servings':2,'ingredients':'5EL Sojasauce\n1 EL Currypulver\n2 TL Zaubergewürz\n1 TL Kreuzkümmel\n1 Prise Salz\n1 EL Sesamöl','steps':''},
 H+'/plan/p1':{'id':'p1','date':D(2),'recipeId':'r1','servings':2,'cooked':False,'created':1},
}
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True)
    ctx.route('**/www.gstatic.com/**',lambda r:r.abort()); ctx.route('**/fonts.*/**',lambda r:r.abort())
    ctx.add_init_script("window.FAKE_UID='u1'; window.FAKE_SEED=%s;"%json.dumps(seed)); ctx.add_init_script(path=os.path.join(HERE,'fakefb.js'))
    pg=ctx.new_page(); pg.on('pageerror',lambda e:print('PAGEERR',e))
    pg.goto('http://127.0.0.1:8798/index.html'); pg.wait_for_function('R.active===true'); pg.wait_for_timeout(400)
    # 0 Tabelle und Regeln
    names=['Currypulver','Salz','Jodsalz','Kräutersalz','Dinkelvollkornmehl','Mandeln, gemahlen','Staubzucker','Preiselbeeren','Currypaste','Basmatireis','Sesamöl','Zimtstangen','Chiliflocken','Kräuter der Provence','Kokosblütenzucker','Zaubergewürz','Bio-Gewürzmischung','Käse']
    print('0 Tabelle:', pg.evaluate('n=>n.map(x=>[x, elTable(x), elRule(x)])', names))
    print('0 Zeile:', pg.evaluate("JSON.stringify(parseIngredient('5EL Sojasauce'))"), pg.evaluate("JSON.stringify(parseIngredient('½ TL Zimt'))"))
    def gericht(tag):
        pg.click('[data-tab=cook]'); pg.wait_for_timeout(200); pg.click('[data-meal=p1]'); pg.wait_for_timeout(300)
        print(tag, '\n  ' + pg.inner_text('.ingprev').replace('\n','\n  '))
    gericht('1 Gericht:')
    pg.screenshot(path=os.path.join(HERE,'l1.png'))
    print('1 Einkauf:', pg.evaluate("JSON.stringify(Object.values(planCalc().buy).map(b=>[b.name,b.amt,b.any]))"))
    # 2 Hinweis antippen → Zaubergewürz, Vorschlag übernehmen
    pg.click('[data-fixart=zauber]'); pg.wait_for_timeout(300)
    print('2 Feld:', pg.inner_text('#f-recipe').replace('\n',' | '))
    pg.screenshot(path=os.path.join(HERE,'l2.png'), full_page=True)
    pg.click('#f-recipe .actions [data-elg="7"]'); pg.wait_for_timeout(300)
    print('2 elg:', pg.evaluate("S.articles.zauber.elg"), '| Feld:', pg.inner_text('#f-recipe').replace('\n',' | '))
    pg.go_back(); pg.wait_for_timeout(300)
    # 3 Kreuzkümmel: Größe nachtragen
    gericht('3 Gericht nach Vorschlag:')
    pg.click('[data-fixart=kk]'); pg.wait_for_timeout(300)
    print('3 Feld:', pg.inner_text('#f-recipe').replace('\n',' | '))
    pg.fill('#f-fixsize','30 g'); pg.click('#fixSizeBtn'); pg.wait_for_timeout(300)
    print('3 Lots:', pg.evaluate("JSON.stringify(S.articles.kk.lots.map(l=>l.size))"), S:=pg.evaluate("S.articles.kk.base"))
    print('3 Feld danach:', pg.inner_text('#f-recipe').replace('\n',' | ') if pg.query_selector('#f-recipe') else '-')
    pg.screenshot(path=os.path.join(HERE,'l3.png'), full_page=True)
    pg.go_back(); pg.wait_for_timeout(300)
    gericht('4 Gericht komplett:')
    pg.screenshot(path=os.path.join(HERE,'l4.png'))
    # 5 Kochen
    pg.evaluate("cook('p1')"); pg.wait_for_timeout(200)
    print('5 nach Kochen:', pg.evaluate("JSON.stringify(['soja','curry','zauber','kk'].map(i=>[i, S.articles[i].lots.map(l=>Math.round(l.qty*l.size*10)/10)]))"))
    b.close()
