# Durchlauf: Rezepte bewerten (zwei Personen), Zeiten, Tags und Filter, Kategorien zuklappen, Wischen in „Kochen“.
# Aufruf: python3 tests/rezepte.py   (braucht: pip install playwright && playwright install chromium)
import http.server,threading,functools,json,datetime,os
HERE=os.path.dirname(os.path.abspath(__file__)); DOCS=os.path.join(HERE,'..','docs')
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',8796),functools.partial(Q,directory=DOCS));threading.Thread(target=s.serve_forever,daemon=True).start()
T=datetime.date.today(); D=lambda n:(T+datetime.timedelta(days=n)).isoformat()
H='households/h1'
seed={H:{'members':['u1','u2'],'inviteCode':'123456','names':{'u1':'Anna','u2':'Max'},'meta':{'v':4,'planDays':7}},
 H+'/recipes/r1':{'id':'r1','name':'Palatschinken','servings':4,'ingredients':'2 Eier','steps':'','ratings':{'u2':4},'tags':['Süß','Schnell']},
 H+'/recipes/r2':{'id':'r2','name':'Gulasch','servings':4,'ingredients':'1 kg Rindfleisch','steps':'','prepTime':30,'cookTime':120,'tags':['Fleisch']},
 H+'/recipes/r3':{'id':'r3','name':'Kaiserschmarrn','servings':2,'ingredients':'3 Eier','steps':''},
}
cats=['Obst & Gemüse','Kühlregal','Brot & Gebäck']
for i,c in enumerate(cats):
    for j in range(3): seed[H+f'/articles/a{i}{j}']={'id':f'a{i}{j}','name':f'{c.split()[0]} {j}','cat':c,'mode':'count','unit':'Stk','lots':[{'id':f'l{i}{j}','qty':1,'bought':D(-1)}]}
seed[H+'/articles/a00']['lots'][0]['expires']=D(-1)
def swipe(pg, dx):
    pg.evaluate("""dx => { const y = 400, x0 = 200;
      const t = (x) => new Touch({identifier: 1, target: document.querySelector('#view'), clientX: x, clientY: y});
      document.querySelector('#view').dispatchEvent(new TouchEvent('touchstart', {touches: [t(x0)], changedTouches: [t(x0)], bubbles: true}));
      document.querySelector('#view').dispatchEvent(new TouchEvent('touchend', {touches: [], changedTouches: [t(x0 + dx)], bubbles: true})); }""", dx)
    pg.wait_for_timeout(250)
    return pg.evaluate("UI.tab + '/' + UI.cookView")
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True)
    ctx.route('**/www.gstatic.com/**',lambda r:r.abort()); ctx.route('**/fonts.*/**',lambda r:r.abort())
    ctx.add_init_script("window.FAKE_UID='u1'; window.FAKE_SEED=%s;"%json.dumps(seed)); ctx.add_init_script(path=os.path.join(HERE,'fakefb.js'))
    pg=ctx.new_page(); pg.on('pageerror',lambda e:print('PAGEERR',e))
    pg.goto('http://127.0.0.1:8796/index.html'); pg.wait_for_function('R.active===true'); pg.wait_for_timeout(400)
    # 1 Kategorien zuklappen
    pg.click('[data-togglecat="Obst & Gemüse"]'); pg.wait_for_timeout(200)
    print('1 Gruppen:', pg.eval_on_selector_all('.group h2', 'e=>e.map(x=>x.innerText.replace(/\\n/g," "))'), '| Zeilen:', pg.eval_on_selector_all('.row', 'e=>e.length'))
    print('1 gespeichert:', pg.evaluate("localStorage.getItem('haushoed:collapsed')"))
    pg.screenshot(path=os.path.join(HERE,'r1.png'))
    pg.fill('#q','Obst'); pg.wait_for_timeout(200)
    print('1 Suche „Obst“ zeigt:', pg.eval_on_selector_all('.row', 'e=>e.length'), 'Zeilen')
    pg.fill('#q',''); pg.wait_for_timeout(200)
    pg.reload(); pg.wait_for_function('R.active===true'); pg.wait_for_timeout(300)
    print('1 nach Neuladen zu:', pg.evaluate("[...UI.collapsed]"))
    # 2 Wischen
    pg.evaluate("UI.cookView='wishes'")
    print('2 Wischen:', [swipe(pg,-150) for _ in range(5)], '| zurück:', [swipe(pg,150) for _ in range(5)])
    # 3 Rezepte: Liste und Filter
    pg.click('[data-tab=cook]'); pg.wait_for_timeout(150); pg.click('[data-cookview=recipes]'); pg.wait_for_timeout(200)
    print('3 Liste:', pg.eval_on_selector_all('.meal', 'e=>e.map(x=>x.innerText.replace(/\\n/g," | "))'))
    print('3 Tag-Chips:', pg.eval_on_selector_all('[data-tagfilter]', 'e=>e.map(x=>x.innerText)'))
    pg.click('[data-tagfilter="Süß"]'); pg.wait_for_timeout(150)
    print('3 Filter Süß:', pg.eval_on_selector_all('.meal .name', 'e=>e.map(x=>x.innerText)'))
    pg.click('[data-tagfilter="Fleisch"]'); pg.wait_for_timeout(150)
    print('3 Süß + Fleisch:', pg.inner_text('#view').replace('\n',' | '))
    pg.click('#view .emptystate [data-act=rclear]'); pg.wait_for_timeout(150)
    # 4 Rezept bearbeiten: Bewertung, Zeiten, Tags
    pg.click('[data-recipe=r3]'); pg.wait_for_timeout(300)
    pg.click('[data-star="5"]'); pg.wait_for_timeout(150)
    print('4 nach 5 Sterne:', pg.evaluate("JSON.stringify(S.recipes.r3.ratings)"), '| Schreibart:', pg.evaluate("JSON.stringify(FAKE.writes.slice(-1))"))
    pg.click('[data-star="5"]'); pg.wait_for_timeout(150)
    print('4 nochmal 5 (zurück):', pg.evaluate("JSON.stringify(S.recipes.r3.ratings)"), pg.inner_text('#r-rhint'))
    pg.click('[data-star="4"]'); pg.wait_for_timeout(150)
    pg.fill('#r-prep','15'); pg.fill('#r-cook','20')
    pg.click('#r-tag'); pg.wait_for_timeout(100)
    print('4 Vorschläge:', pg.eval_on_selector_all('#r-tagsugg [data-addtag]', 'e=>e.map(x=>x.innerText)'))
    pg.click('#r-tagsugg [data-addtag="Süß"]'); pg.type('#r-tag','schnell'); pg.keyboard.press('Enter'); pg.type('#r-tag','Mehlspeise, Österreichisch'); pg.wait_for_timeout(100)
    print('4 Tags im Blatt:', pg.eval_on_selector_all('#r-tags [data-deltag]', 'e=>e.map(x=>x.dataset.deltag)'), '| Feld:', pg.input_value('#r-tag'))
    pg.locator('#r-stars').scroll_into_view_if_needed(); pg.screenshot(path=os.path.join(HERE,'r2.png'))
    # Max bewertet in der Zwischenzeit (kommt über die Live-Verbindung)
    pg.evaluate("FAKE.store.set('households/h1/recipes/r3', {...FAKE.store.get('households/h1/recipes/r3'), ratings: {u1: 4, u2: 2}})")
    pg.evaluate("S.recipes.r3 = {...S.recipes.r3, ratings: {u1: 4, u2: 2}}")
    pg.click('#r-save'); pg.wait_for_timeout(300)
    r3=pg.evaluate("JSON.stringify(S.recipes.r3)")
    print('4 gespeichert:', r3)
    print('4 Liste:', pg.eval_on_selector_all('.meal', 'e=>e.map(x=>x.innerText.replace(/\\n/g," | "))'))
    pg.screenshot(path=os.path.join(HERE,'r3.png'))
    print('4 Tag-Chips:', pg.eval_on_selector_all('[data-tagfilter]', 'e=>e.map(x=>x.innerText)'))
    # 5 Sortieren
    for k in ['rating','time','name']:
        pg.click(f'[data-rsort={k}]'); pg.wait_for_timeout(120)
        print('5 Sortierung', k, ':', pg.eval_on_selector_all('.meal .name', 'e=>e.map(x=>x.innerText)'))
    pg.click('[data-rsort=rating]'); pg.wait_for_timeout(120)
    print('5 gemerkt:', pg.evaluate("localStorage.getItem('haushoed:recipeSort')"))
    pg.screenshot(path=os.path.join(HERE,'r4.png'))
    # 6 Tags verwalten
    pg.click('[data-act=rfilter]'); pg.wait_for_timeout(250); pg.click('#rf-tags'); pg.wait_for_timeout(250)
    print('6 Liste:', pg.eval_on_selector_all('#sheet .lot .l', 'e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    pg.click('[data-tedit="Mehlspeise"]'); pg.fill('#t-edit','Süß'); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
    print('6 zusammengeführt:', pg.evaluate("JSON.stringify(S.recipes.r3.tags)"), '| Meldung:', pg.inner_text('#snackMsg'), '| Schreibart:', pg.evaluate("JSON.stringify(FAKE.writes.slice(-1))"))
    pg.click('#snackUndo'); pg.wait_for_timeout(200)
    print('6 rückgängig:', pg.evaluate("JSON.stringify(S.recipes.r3.tags)"))
    pg.click('[data-tedit="Schnell"]'); pg.fill('#t-edit','schnell & einfach'); pg.click('[data-tsave]'); pg.wait_for_timeout(200)
    print('6 umbenannt:', pg.evaluate("JSON.stringify([S.recipes.r1.tags, S.recipes.r3.tags])"))
    pg.click('[data-tdel="Fleisch"]'); pg.wait_for_timeout(100); print('6 erster Tipp:', pg.inner_text('[data-tdel="Fleisch"]'))
    pg.click('[data-tdel="Fleisch"]'); pg.wait_for_timeout(200)
    print('6 gelöscht:', pg.evaluate("JSON.stringify(S.recipes.r2.tags)"), '| Liste:', pg.eval_on_selector_all('#sheet .lot .l', 'e=>e.map(x=>x.innerText.replace(/\\n/g," "))'))
    pg.screenshot(path=os.path.join(HERE,'r5.png'))
    pg.click('#close'); pg.wait_for_timeout(200)
    # 7 Einplanen und Wünschen mit Tag-Filter
    pg.evaluate("openPicker(today())"); pg.wait_for_timeout(250)
    pg.click('#sheet [data-ptag="Süß"]'); pg.wait_for_timeout(150)
    print('7 Einplanen, Süß:', pg.eval_on_selector_all('#p-list [data-pickrecipe] .name', 'e=>e.map(x=>x.innerText)'))
    pg.click('#sheet [data-ptag="Österreichisch"]'); pg.wait_for_timeout(150)
    print('7 Süß + Österreichisch:', pg.eval_on_selector_all('#p-list [data-pickrecipe] .name', 'e=>e.map(x=>x.innerText)'))
    pg.screenshot(path=os.path.join(HERE,'r6.png'))
    pg.click('#close'); pg.wait_for_timeout(200)
    pg.evaluate("openWishPicker()"); pg.wait_for_timeout(250)
    pg.click('#sheet [data-wtag="schnell & einfach"]'); pg.wait_for_timeout(150)
    print('7 Wünschen, schnell & einfach:', pg.eval_on_selector_all('#wp-list [data-wishpick] .name', 'e=>e.map(x=>x.innerText)'))
    b.close()
