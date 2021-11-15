from string import Formatter
import string
import yaml
import re
import sys
import itertools
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

ARG_NAME = re.compile(r"[^.\[]+")

class TempfileArg:
    def __init__(self, suffix=None, prefix=None, dir=None):
        self.tmpfiles = {}
        self.dir_ = dir
        self.suffix = suffix
        self.prefix = prefix

    def reset(self):
        self.tmpfiles = {}

    def __getattr__(self, attr):
        if attr in self.tmpfiles:
            return self.tmpfiles[attr]

        try:
            return super().__getattr__(attr)
        except AttributeError:
            h, f = tempfile.mkstemp(prefix=self.prefix or attr, suffix=self.suffix, dir=self.dir_)
            os.close(h)
            self.tmpfiles[attr] = f
            return self.tmpfiles[attr]

class ScriptTemplate:
    def __init__(self, name, template):
        self.name = name
        self._tmpl = template
        self.fragment = template.get('fragment', False)
        assert 'cmds' in template, f'{name} missing "cmds"'
        self.template = template['cmds'].strip()

        self.serial = template.get('serial', False)
        self._ss = None
        self.inherited_semaphores = {}
        self.parse()

    def set_script(self, script):
        self.script = script

    @property
    def serial_semaphore(self):
        if self._ss is None:
            assert self.script is not None, f"set_script necessary before obtaining semaphore"
            self._ss = Sem(f'{self.script.ns}:{self.name}:serial', 1)

        return self._ss

    def parse(self):
        f = Formatter()

        out = []
        v = []
        try:
            for e in f.parse(self.template):
                fieldname = e[1]
                if fieldname is not None:
                    arg_name = ARG_NAME.match(fieldname)
                    assert arg_name is not None, fieldname
                    arg_name = arg_name.group(0)

                    if arg_name[0] in string.digits:
                        raise ValueError(f"bmk3 templates do not support positional arguments: {arg_name}.")
                    v.append(arg_name)

                out.append(e)
        except ValueError as err:
            print(err, file=sys.stderr)
            print(f"when parsing template '{self.name}':", file=sys.stderr)
            print(self.template, file=sys.stderr)
            sys.exit(1) # TODO

        self.parsed = out
        self._varrefs = v
        self.variables = set(v)

    def expand_templates(self, templates):
        parsed = self.parsed
        changed = True

        while changed:
            changed = False
            out = []
            for x in parsed:
                fieldname = x[1]

                if fieldname is not None:
                    arg_name = ARG_NAME.match(fieldname)
                    assert arg_name is not None, fieldname
                    arg_name = arg_name.group(0)

                    if arg_name == 'templates':
                        assert x[2] == '' and x[3] is None, f"Don't support ! and : for template[]"
                        tmpl = fieldname[len('templates['):][:-1]
                        changed = True
                        if x[0]:
                            out.append((x[0], None, '', None))

                        out.extend(templates[tmpl].parsed)
                        self.serial = self.serial or templates[tmpl].serial

                        if templates[tmpl].serial:
                            self.inherited_semaphores[templates[tmpl].serial_semaphore.name] = templates[tmpl].serial_semaphore

                        self.inherited_semaphores.update(templates[tmpl].inherited_semaphores)
                    else:
                        out.append(x)
                else:
                    out.append(x)

            parsed = out

        template = []
        for x in parsed:
            template.append(x[0])

            if x[1] is not None:
                out = "{" + x[1]
                if x[2]: out = out + "!" + x[2]
                if x[3]: out = out + ":" + x[3]
                out = out + "}"
                template.append(out)

        self.template = ''.join(template)
        self.parse()

    def generate(self, varvals, filters = None):
        vk = set(varvals.keys())
        not_provided = self.variables - vk

        tmpfileobj = None
        if 'TempFile' in not_provided:
            not_provided.remove('TempFile')
            tmpfileobj = TempfileArg()

        if len(not_provided):
            raise KeyError(f"Variables {not_provided} not specified for rule {self.name}")


        semdict = {}
        semdict['_serial'] = self.serial
        if self.serial:
            semdict['_semaphores'] = [self.serial_semaphore]
        else:
            semdict['_semaphores'] = []

        semdict['_semaphores'].extend(self.inherited_semaphores.values())

        varorder = []
        varcontents = []
        for v in self.variables:
            varorder.append(v)
            if v == 'TempFile':
                varcontents.append([tmpfileobj])
            elif isinstance(varvals[v], list):
                # this means that lists must be doubly-nested [[]] to be treated as singletons
                varcontents.append(varvals[v])
            else:
                varcontents.append([varvals[v]])

        for x in itertools.product(*varcontents):
            assign = dict([(v, xx) for v, xx in zip(varorder, x)])

            if filters and self.name in filters:
                if not self.check_assignment(assign, filters[self.name]):
                    continue

            s = self.template.format(**assign)

            if tmpfileobj:
                assign['TempFile'] = tmpfileobj.tmpfiles
                tmpfileobj.reset()

            assign.update(semdict)
            yield assign, s

    def check_assignment(self, assign, filters):
        gl = dict(assign)
        for e in filters['ensure_all']:
            if not eval(e, gl, {}):
                return False

        return True

    def __str__(self):
        return self.template #f"ScriptTemplate({self.name}, {repr(self.template)})"

    __repr__ = __str__

class Script:
    def __init__(self, script, ns = ''):
        self.script = script
        self.ns = ns
        self.cwd = os.path.dirname(os.path.realpath(script))
        self._system, self._variables, self._templates, r = self._loader(self.script)

        for t in self._templates:
            self._templates[t].set_script(self)

        self.filters = r.get('filters', {})

    def _loader(self, script):
        with open(script, "r") as f:
            contents = yaml.safe_load(f)

            system = {}
            variables = {}
            templates = {}
            filters = {}

            if 'import' in contents:
                system['import'] = contents['import']
                for f in contents['import']:
                    _, v, t, r = self._loader(os.path.join(self.cwd, f))

                    # TODO: detect overwriting?
                    variables.update(v)
                    for tt in t:
                        templates.update({tt: t[tt]})
                        if t[tt].fragment:
                            templates[tt].fragment = False

                    for k in r:
                        if k == 'filters':
                            filters.update(r[k])
                        else:
                            raise NotImplementedError(f"Unsupported return key {k}")

            local_templates = contents.get('templates', {})
            local_templates = dict([(v, ScriptTemplate(v, local_templates[v])) for v in local_templates])

            variables.update(contents.get('variables', {}))
            templates.update(local_templates)
            filters.update(contents.get('filters', {}))

            return system, variables, templates, {'filters': filters}

    def generate(self, template_vars, template_filter = lambda x: True):
        for t in self.templates:
            tmpl = self.templates[t]
            if not template_filter(tmpl):
                logger.debug(f'{tmpl.name} filtered out by template_filter')
                continue

            if tmpl.fragment:
                logger.debug(f'{tmpl.name} is a fragment, ignoring when generating')
                continue

            for g in self.templates[t].generate(template_vars, filters=self.filters):
                yield t, g

    @property
    def variables(self):
        return self._variables

    @property
    def templates(self):
        return self._templates


class BMK3:
    def __init__(self):
        pass

    def load_scripts(self, scriptfiles, strip_prefix = ''):
        out = []
        nss = set()
        for f in scriptfiles:
            ns = os.path.dirname(f)[len(strip_prefix):]
            assert ns not in nss, f"Internal error: Duplicate namespace {ns}"
            nss.add(ns)

            s = Script(f, ns)
            out.append(s)

        self.scripts = out
        return out

    def update_variables(self, variables):
        for s in self.scripts:
            s.variables.update(variables)

    def expand_templates(self):
        # TODO: toposort and one-pass
        for s in self.scripts:
            for t in s.templates:
                s.templates[t].expand_templates(s.templates)


    def generate(self, template_filter = lambda x: True):
        for s in self.scripts:
            for t, g in s.generate(s.variables, template_filter):
                yield s, t, g

class Sem:
    """A semaphore specification"""
    def __init__(self, name, count):
        self.name = name
        self.count = count

    def __eq__(self, other):
        return isinstance(other, Sem) and other.name == self.name and other.count == self.count

    def __str__(self):
        return f"Semaphore(name={self.name}, count={self.count})"

    __repr__ = __str__
