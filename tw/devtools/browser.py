import wsgiref.simple_server as ws, webob as wo, tw.core as twc
import pkg_resources as pr


class Page(twc.Widget):
    id = None

class Index(Page):
    template = "genshi:tw.devtools.templates.wb_index"

class Welcome(Page):
    template = "genshi:tw.devtools.templates.wb_welcome"

class List(Page):
    modules = twc.Variable()
    def prepare(self):
        super(List, self).prepare()
        self.modules = [ep.module_name
                        for ep in pr.iter_entry_points('toscawidgets.widgets')
                        if not ep.module_name.endswith('.samples')]
    template = "genshi:tw.devtools.templates.wb_list"


class BrowseWidget(twc.Widget):
    id = None
    template = 'genshi:tw.devtools.templates.wb_widget'
    resources = [twc.CSSLink(modname='tw.devtools', filename='static/browser.css')]
    name = twc.Variable()
    widget = twc.Variable()
    params = twc.Variable()
    child_params = twc.Variable()
    demo = twc.Variable()

    def prepare(self):
        super(BrowseWidget, self).prepare()
        if self.value:
            self.name, self.widget, self.demo = self.value
            self.params = sorted(self.widget._params.values(), key=lambda p: p._seq)
            self.child_params = [p for p in self.widget._all_params.values()
                                            if p.child_param and not p.internal]
            self.child_params.sort(key=lambda p: p._seq)
            req_prm = [p.name for p in self.params if p.default is twc.Required]
            if self.demo:
                self.demo = self.demo(id='demo%i' % self.repetition, parent=self).req()
            elif not req_prm or req_prm == ['id']: # auto demo
                self.demo = self.widget(id='demo', parent=self).req()
            else:
                self.demo = None

class BrowseModule(twc.RepeatingWidget):
    template = 'genshi:tw.devtools.templates.wb_module'
    module = twc.Param('module to display')
    child = BrowseWidget
    extra_reps = 0

    def _load_ep(self, module):
        for ep in pr.iter_entry_points('toscawidgets.widgets'):
            if ep.module_name == module:
                return ep.load()
        raise Exception('module not found')

    def _get_widgets(self, module=None, modname=None):
        if not module:
            module = self._load_ep(modname)
        widgets = []
        for attr in dir(module):
            widget = getattr(module, attr)
            if isinstance(widget, twc.widgets.WidgetMeta):
                widgets.append((attr, widget))
        widgets.sort(key=lambda t: t[1]._seq)
        return widgets

    def prepare(self):
        demo_for = {}
        try:
            samples = self._get_widgets(self._load_ep(self.module + '.samples'))
            for n,s in samples:
                df = s.__dict__.get('demo_for', s.__mro__[1])
                demo_for[df] = s
        except Exception, e:
            pass
        widgets = self._get_widgets(self._load_ep(self.module))
        self.value = [(n, w, demo_for.get(w)) for n, w in widgets]
        super(BrowseModule, self).prepare()

paths = {
    '/': Index(),
    '/welcome': Welcome(),
    '/list': List(),
}


def widget_browser(environ, start_response):
    req = wo.Request(environ)
    resp = wo.Response(request=req, content_type="text/html; charset=UTF8")
    if req.path in paths:
        resp.body = paths[req.path].idisplay().encode('utf-8')
    else:
        resp.body = BrowseModule.idisplay(module = req.path.lstrip('/')).encode('utf-8')
    return resp(environ, start_response)

wb_app = twc.TwMiddleware(widget_browser)

from paste.script import command as pc

class WbCommand(pc.Command):
    def command(self):
        ws.make_server('', 8000, wb_app).serve_forever()
    group_name = 'toscawidgets'
    summary = 'Browse widgets'
    min_args = 0
    max_args = 0
    usage = 'blah'

    parser = pc.Command.standard_parser(verbose=True)


if __name__ == '__main__':
    ws.make_server('', 8000, wb_app).serve_forever()
