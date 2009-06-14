import webob as wo, webtest as wt, tw.core as twc, tw.tests, os, testapi

js = twc.JSLink(link='paj')
css = twc.CSSLink(link='joe')
jssrc = twc.JSSource(src='bob')

html = "<html><head><title>a</title></head><body>hello</body></html>"

inject_widget = twc.Widget(id='a', template='b', resources=[js])

def simple_app(environ, start_response):
    req = wo.Request(environ)
    ct = 'text/html' if req.path == '/' else 'test/plain'
    resp = wo.Response(request=req, content_type="%s; charset=UTF8" % ct)
    inject_widget.req().prepare()
    resp.body = html
    return resp(environ, start_response)
mw = twc.TwMiddleware(simple_app)
tst_mw = wt.TestApp(mw)


class TestResources(object):
    def setUp(self):
        testapi.setup()

    def test_res_collection(self):
        wa = twc.Widget(id='a', template='b').req()
        wb = twc.Widget(id='b', template='b', resources=[js,css]).req()

        rl = testapi.request(1)
        wa.prepare()
        assert(len(rl.get('resources', [])) == 0)
        wb.prepare()
        for r in rl['resources']:
            assert(any(isinstance(r, b) for b in [js,css]))
        rl = testapi.request(2)
        assert(len(rl.get('resources', [])) == 0)

    def test_res_nodupe(self):
        wa = twc.Widget(id='a', template='b', resources=[js]).req()
        wb = twc.Widget(id='b', template='b', resources=[twc.JSLink(link='paj')]).req()
        wc = twc.Widget(id='c', template='b', resources=[twc.JSLink(link='test')]).req()
        wd = twc.Widget(id='d', template='b', resources=[css]).req()
        we = twc.Widget(id='e', template='b', resources=[twc.CSSLink(link='joe')]).req()

        rl = testapi.request(1)
        wa.prepare()
        wb.prepare()
        r = rl['resources']
        assert(len(rl['resources']) == 1)
        wc.prepare()
        assert(len(rl['resources']) == 2)
        wd.prepare()
        we.prepare()
        assert(len(rl['resources']) == 3)


    #--
    # ResourcesApp
    #--
    def test_not_found(self):
        #assert(tst_mw.get('/fred', expect_errors=True).status == '404 Not Found')
        assert(tst_mw.get('/resources/test', expect_errors=True).status == '404 Not Found')

    def test_serve(self):
        mw.resources.register('tw.tests', 'templates/simple_genshi.html')
        fcont = open(os.path.join(os.path.dirname(tw.tests.__file__), 'templates/simple_genshi.html')).read()
        assert(tst_mw.get('/resources/tw.tests/templates/simple_genshi.html').body == fcont)
        assert(tst_mw.get('/resources/tw.tests/templates/notexist', expect_errors=True).status == '404 Not Found')

    def test_dir_traversal(self): # check for potential security flaw
        mw.resources.register('tw.tests', 'templates/simple_genshi.html')
        assert(tst_mw.get('/resources/tw.tests/__init__.py', expect_errors=True).status == '404 Not Found')
        assert(tst_mw.get('/resources/tw.tests/templates/../__init__.py', expect_errors=True).status == '404 Not Found')

    def test_different_file(self):
        mw.resources.register('tw.tests', 'templates/simple_genshi.html')
        assert(tst_mw.get('/resources/tw.tests/simple_kid.kid', expect_errors=True).status == '404 Not Found')

    def test_zipped(self):
        # assumes webtest is installed as a zipped egg
        mw.resources.register('webtest', '__init__.py')
        assert(tst_mw.get('/resources/webtest/__init__.py').body.startswith('# (c) 2005 Ian'))

    #--
    # Links register resources
    #--
    def test_link_reg(self):
        testapi.request(1, mw)
        wa = twc.JSLink(modname='tw.tests', filename='templates/simple_mako.mak').req()
        wa.prepare()
        assert(wa.link == '/resources/tw.tests/templates/simple_mako.mak')
        tst_mw.get(wa.link)

    def test_mime_type(self):
        testapi.request(1, mw)
        wa = twc.JSLink(modname='tw.tests', filename='templates/simple_genshi.html').req()
        wa.prepare()
        resp = tst_mw.get(wa.link)
        assert(resp.content_type == 'text/html')
        assert(resp.charset == 'UTF-8')

    def test_auto_modname(self):
        pass  # TBD

    #--
    # Resource injector
    #--
    def test_inject_head(self):
        rl = testapi.request(1, mw)
        out = twc.inject_resources(html, [js.req()])
        assert(out == '<html><head><script type="text/javascript" src="paj"></script><title>a</title></head><body>hello</body></html>')

    def test_inject_body(self):
        rl = testapi.request(1, mw)
        out = twc.inject_resources(html, [jssrc.req()])
        assert(out == '<html><head><title>a</title></head><body>hello<script type="text/javascript">bob</script></body></html>')

    def test_inject_both(self):
        rl = testapi.request(1, mw)
        out = twc.inject_resources(html, [js.req(), jssrc.req()])
        assert(out == '<html><head><script type="text/javascript" src="paj"></script><title>a</title></head><body>hello<script type="text/javascript">bob</script></body></html>')

    def test_detect_clear(self):
        widget = twc.Widget(id='a', template='b', resources=[js])
        rl = testapi.request(1, mw)
        assert(len(rl.get('resources', [])) == 0)
        widget.req().prepare()
        assert(len(rl.get('resources', [])) == 1)
        out = twc.inject_resources(html)
        assert(len(rl.get('resources', [])) == 0)

    #--
    # General middleware
    #--
    def test_mw_resourcesapp(self):
        testapi.request(1)
        mw.resources.register('tw.tests', 'templates/simple_genshi.html')
        fcont = open(os.path.join(os.path.dirname(tw.tests.__file__), 'templates/simple_genshi.html')).read()
        print tst_mw.get('/resources/tw.tests/templates/simple_genshi.html').body
        assert(tst_mw.get('/resources/tw.tests/templates/simple_genshi.html').body == fcont)

    def test_mw_clear_rl(self):
        rl = testapi.request(1)
        rl['blah'] = 'lah'
        tst_mw.get('/')
        assert(rl == {})

    def test_mw_inject(self):
        testapi.request(1, mw)
        widget = twc.Widget(id='a', template='b', resources=[js]).req().prepare()
        assert(tst_mw.get('/').body == '<html><head><script type="text/javascript" src="paj"></script><title>a</title></head><body>hello</body></html>')

    def test_mw_inject_html_only(self):
        testapi.request(1, mw)
        widget = twc.Widget(id='a', template='b', resources=[js]).req().prepare()
        assert(tst_mw.get('/plain').body == html)
