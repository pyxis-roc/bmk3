from string import Formatter
import string
import yaml
import re
import sys
import itertools
import tempfile
import os

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
        self.template = template.strip()
        self.parse()

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
                        assert x[2] is '' and x[3] is None, f"Don't support ! and : for template[]"
                        tmpl = fieldname[len('templates['):][:-1]
                        changed = True
                        if x[0]:
                            out.append((x[0], None, '', None))

                        out.extend(templates[tmpl].parsed)
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

    def generate(self, varvals):
        vk = set(varvals.keys())
        not_provided = self.variables - vk

        tmpfileobj = None
        if 'TempFile' in not_provided:
            not_provided.remove('TempFile')
            tmpfileobj = TempfileArg()

        if len(not_provided):
            raise KeyError(f"Variables {not_provided} not specified for rule {self.name}")

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

            s = self.template.format(**assign)

            if tmpfileobj:
                assign['TempFile'] = tmpfileobj.tmpfiles
                tmpfileobj.reset()

            yield assign, s

    def __str__(self):
        return self.template #f"ScriptTemplate({self.name}, {repr(self.template)})"

    __repr__ = __str__

class Script:
    def __init__(self, script):
        self.script = script
        self.cwd = os.path.dirname(os.path.realpath(script))
        self._variables, self._templates = self._loader(self.script)

    def _loader(self, script):
        with open(script, "r") as f:
            contents = yaml.safe_load(f)

            variables = {}
            templates = {}

            if 'import' in contents:
                for f in contents['import']:
                    v, t = self._loader(f)

                    # TODO: detect overwriting?
                    variables.update(v)
                    templates.update(t)

            local_templates = contents.get('templates', {})
            local_templates = dict([(v, ScriptTemplate(v, local_templates[v])) for v in local_templates])

            variables.update(contents.get('variables', {}))
            templates.update(local_templates)

            return variables, templates

    @property
    def variables(self):
        return self._variables

    @property
    def templates(self):
        return self._templates
