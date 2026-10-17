# Durchlauf: Rezepte nach Bewertungen einzelner Personen, Tags und Zeiten filtern, Filter speichern;
# Kinderrolle vergeben und die Ansicht eines Kindes.
# Aufruf: python3 tests/kinder.py   (braucht: pip install playwright && playwright install chromium)
import http.server,threading,functools,json,datetime,os
HERE=os.path.dirname(os.path.abspath(__file__)); DOCS=os.path.join(HERE,'..','docs')
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',8793),functools.partial(Q,directory=DOCS));threading.Thread(target=s.serve_forever,daemon=True).start()
T=datetime.date.today(); D=lambda n:(T+datetime.timedelta(days=n)).isoformat()
H='households/h1'
rec=lambda i,name,ratings,prep=None,cook=None,tags=[]: {'id':i,'name':name,'servings':4,'ingredients':'200 g Mehl\n3 Eier\n1 Prise Salz','steps':'Alles verrühren.','ratings':ratings,'prepTime':prep,'cookTime':cook,'tags':tags}
seed={H:{'members':['u1','u2','u3'],'inviteCode':'123456','names':{'u1':'Anna','u2':'Alexander','u3':'Nina'},'meta':{'v':4,'planDays':7}},
 H+'/recipes/r1':rec('r1','Palatschinken',{'u2':2,'u3':5},10,15,['Süß']),
 H+'/recipes/r2':rec('r2','Gulasch',{'u2':3,'u3':5},30,120,['Fleisch']),
 H+'/recipes/r3':rec('r3','Kaiserschmarrn',{'u2':1,'u3':5},15,20,['Süß']),
 H+'/recipes/r4':rec('r4','Spinatknödel',{'u2':2,'u3':3},40,20,[]),
 H+'/recipes/r5':rec('r5','Topfenstrudel',{'u3':5},45,40,['Süß']),
 H+'/plan/p1':{'id':'p1','date':D(1),'recipeId':'r2','servings':4,'cooked':False},
 H+'/wishes/r1':{'id':'r1','recipeId':'r1','by':'u3','created':1,'votes':{'u3':1}},
 H+'/articles/mehl':{'id':'mehl','name':'Mehl','cat':'Backen','mode':'count','unit':'Pkg','lots':[{'id':'m1','qty':1,'bought':D(-1),'size':1000}],'base':'g','packSize':1000},
}
def page(uid, seed_):
    ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True)
    ctx.route('**/www.gstatic.com/**',lambda r:r.abort()); ctx.route('**/fonts.*/**',lambda r:r.abort())
    ctx.add_init_script("window.FAKE_UID='%s'; window.FAKE_SEED=%s;"%(uid,json.dumps(seed_))); ctx.add_init_script(path=os.path.join(HERE,'fakefb.js'))
    pg=ctx.new_page(); pg.on('pageerror',lambda e:print('PAGEERR',e))
    pg.goto('http://127.0.0.1:8793/index.html'); pg.wait_for_function('R.active===true'); pg.wait_for_timeout(400)
    return pg
names=lambda pg: pg.eval_on_selector_all('#view .meal .name', 'e=>e.map(x=>x.innerText)')
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---------- Anna (erwachsen) ----------
    pg=page('u1', seed)
    pg.click('[data-tab=cook]'); pg.wait_for_timeout(150); pg.click('[data-cookview=recipes]'); pg.wait_for_timeout(200)
    print('1 alle:', names(pg))
    pg.click('[data-act=rfilter]'); pg.wait_for_timeout(250)
    print('1 Personen im Filter:', pg.eval_on_selector_all('#sheet [data-rlo]', 'e=>e.map(x=>x.getAttribute("aria-label"))'))
    # Alexander > 1 und < 3 (also 2), Nina > 4 (also 5)
    pg.select_option('[data-rlo=u2]','2'); pg.select_option('[data-rhi=u2]','2'); pg.select_option('[data-rlo=u3]','5'); pg.wait_for_timeout(150)
    print('1 Alexander 2, Nina 5:', names(pg), '|', pg.inner_text('#rf-count'))
    pg.click('#sheet [data-ftag="Süß"]'); pg.wait_for_timeout(100)
    pg.fill('#f-preplo',''); pg.fill('#f-prephi','12'); pg.wait_for_timeout(150)
    print('1 + Süß + Arbeitszeit bis 12:', names(pg), '|', pg.inner_text('#rf-count'))
    pg.fill('#f-prephi',''); pg.keyboard.press('Enter'); pg.wait_for_timeout(150)
    pg.click('#rf-save'); pg.wait_for_timeout(150); print('1 Vorschlag Name:', pg.input_value('#f-sname'))
    pg.fill('#f-sname','Nina liebt, Alex okay'); pg.click('#rf-dosave'); pg.wait_for_timeout(250)
    print('1 gespeichert:', pg.evaluate("JSON.stringify(HH.data.filters.u1)")[:200], '| Schreibart:', pg.evaluate("JSON.stringify(FAKE.writes.slice(-1))"))
    pg.screenshot(path=os.path.join(HERE,'k1.png'), full_page=True)
    pg.click('#close'); pg.wait_for_timeout(200)
    print('1 Liste:', names(pg), '| Zusammenfassung:', pg.inner_text('.fsum'))
    pg.click('[data-act=rclear]'); pg.wait_for_timeout(150); print('1 gelöscht:', len(names(pg)))
    pg.click('[data-rsaved]'); pg.wait_for_timeout(150); print('1 gespeicherten angewandt:', names(pg))
    pg.screenshot(path=os.path.join(HERE,'k2.png'))
    pg.click('[data-rsaved]'); pg.wait_for_timeout(150); print('1 nochmal tippen hebt auf:', len(names(pg)))
    # Kochzeit ab 30
    pg.click('[data-act=rfilter]'); pg.wait_for_timeout(250); pg.fill('#f-cooklo','30'); pg.keyboard.press('Enter'); pg.wait_for_timeout(150)
    print('1 Kochzeit ab 30:', names(pg)); pg.click('#rf-clear'); pg.click('#close'); pg.wait_for_timeout(200)
    # Tag umbenennen zieht gespeicherte Filter nach
    pg.evaluate("renameTag('Süß','Mehlspeise')"); pg.wait_for_timeout(150)
    print('1 Filter nach Umbenennen:', pg.evaluate("JSON.stringify(HH.data.filters.u1[0].tags)"))
    # Kinderrolle
    pg.click('[data-tab=more]'); pg.wait_for_timeout(200)
    print('2 Mitglieder:', pg.inner_text('.members').replace('\n',' | '))
    pg.check('[data-kidrole=u2]'); pg.wait_for_timeout(200)
    print('2 Rolle:', pg.evaluate("JSON.stringify(FAKE.get('households/h1').roles)"), '|', pg.inner_text('#snackMsg'))
    pg.screenshot(path=os.path.join(HERE,'k3.png'), full_page=True)
    # ---------- Alexander (Kind) ----------
    seed2=json.loads(json.dumps(seed)); seed2[H]['roles']={'u2':'child'}
    kp=page('u2', seed2)
    print('3 Reiter sichtbar:', kp.evaluate("getComputedStyle(document.querySelector('.tabs')).display"), '| Bereich:', kp.evaluate("UI.tab+'/'+UI.cookView"), '| Plus:', kp.evaluate("document.querySelector('#fab').hidden"))
    print('3 Wochenplan:', kp.inner_text('#view').replace('\n',' | ')[:220], '| Plus-Knöpfe:', kp.eval_on_selector_all('[data-addmeal]','e=>e.length'))
    kp.screenshot(path=os.path.join(HERE,'k4.png'))
    kp.click('[data-meal=p1]'); kp.wait_for_timeout(300)
    print('3 Gericht:', kp.inner_text('#sheet').replace('\n',' | '), '| Eingabefelder:', kp.eval_on_selector_all('#sheet input, #sheet textarea','e=>e.length'))
    kp.click('#sheet [data-star="4"]'); kp.wait_for_timeout(200)
    print('3 bewertet:', kp.evaluate("JSON.stringify(S.recipes.r2.ratings)"), '| Schreibart:', kp.evaluate("JSON.stringify(FAKE.writes.slice(-1))"))
    kp.screenshot(path=os.path.join(HERE,'k5.png'))
    kp.click('#close'); kp.wait_for_timeout(200)
    kp.click('[data-cookview=recipes]'); kp.wait_for_timeout(200)
    print('4 Rezepte:', kp.eval_on_selector_all('#view .meal', 'e=>e.map(x=>x.innerText.replace(/\\n/g," | "))')[:3], '| Sortierung:', kp.eval_on_selector_all('[data-rsort]','e=>e.map(x=>x.innerText)'))
    kp.click('[data-act=rfilter]'); kp.wait_for_timeout(250)
    print('4 Filter-Blatt:', [x for x in ['#f-preplo','#f-cooklo','#rf-tags','[data-rlo=u3]','[data-ftag]'] if kp.query_selector(x)])
    kp.click('#close'); kp.wait_for_timeout(200)
    kp.click('[data-recipe=r4]'); kp.wait_for_timeout(300)
    print('4 Rezept:', kp.inner_text('#sheet').replace('\n',' | '))
    kp.click('#close'); kp.wait_for_timeout(200)
    kp.click('[data-cookview=wishes]'); kp.wait_for_timeout(200)
    print('5 Wünsche:', kp.inner_text('#view').replace('\n',' | ')[:200], '| Plus:', kp.evaluate("document.querySelector('#fab').hidden"))
    kp.click('[data-wish=r1]'); kp.wait_for_timeout(300)
    print('5 Wunsch:', kp.inner_text('#sheet').replace('\n',' | '), '| Einplanen:', kp.eval_on_selector_all('[data-planday]','e=>e.length'))
    kp.click('#close'); kp.wait_for_timeout(200)
    kp.click('[data-act=wishadd]'); kp.wait_for_timeout(300)
    print('5 Wunsch-Auswahl:', kp.inner_text('#wp-list').replace('\n',' | ')[:160], '| Neues Rezept:', bool(kp.query_selector('#wp-new')))
    kp.click('#wp-list [data-wishpick=r3]'); kp.wait_for_timeout(250); print('5 gewünscht:', kp.evaluate("!!S.wishes.r3"))
    # Wischen bleibt in „Kochen“
    def swipe(dx):
        kp.evaluate("""dx => { const t = x => new Touch({identifier:1,target:document.querySelector('#view'),clientX:x,clientY:400});
          document.querySelector('#view').dispatchEvent(new TouchEvent('touchstart',{touches:[t(200)],changedTouches:[t(200)],bubbles:true}));
          document.querySelector('#view').dispatchEvent(new TouchEvent('touchend',{touches:[],changedTouches:[t(200+dx)],bubbles:true})); }""", dx); kp.wait_for_timeout(200)
        return kp.evaluate("UI.tab+'/'+UI.cookView")
    print('6 Wischen:', [swipe(-150) for _ in range(3)], [swipe(150) for _ in range(3)])
    kp.evaluate("goTab('stock')"); kp.wait_for_timeout(150); print('6 Vorrat erzwingen:', kp.evaluate("UI.tab"))
    # Kurzbefehl wirkt nicht; nach Neuladen sofort Kinderansicht (ohne auf den Haushalt zu warten)
    kp.goto('http://127.0.0.1:8793/index.html?do=use'); kp.wait_for_timeout(60)
    print('7 sofort nach Start:', kp.evaluate("UI.tab"), '| Reiter:', kp.evaluate("getComputedStyle(document.querySelector('.tabs')).display")); kp.wait_for_timeout(600)
    print('7 Verbraucht-Blatt offen:', kp.evaluate("!!document.querySelector('#qu-q')"))
    # Rolle wird live zurückgenommen
    kp.evaluate("FAKE.remoteUpdate('households/h1', {'roles.u2': null})"); kp.wait_for_timeout(300)
    print('8 wieder erwachsen:', kp.evaluate("getComputedStyle(document.querySelector('.tabs')).display"), kp.evaluate("kid()"))
    b.close()
s.shutdown()
