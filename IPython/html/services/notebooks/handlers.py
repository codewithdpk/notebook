"""Tornado handlers for the notebooks web service.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from tornado import web

from zmq.utils import jsonapi

from IPython.utils.jsonutil import date_default

from ...base.handlers import IPythonHandler

#-----------------------------------------------------------------------------
# Notebook web service handlers
#-----------------------------------------------------------------------------


class NotebookRootHandler(IPythonHandler):

    @web.authenticated
    def get(self):
        """get returns a list of notebooks from the location
        where the server was started."""
        nbm = self.notebook_manager
        notebooks = nbm.list_notebooks("/")
        self.finish(jsonapi.dumps(notebooks))

    @web.authenticated
    def post(self):
        """post creates a notebooks in the directory where the
        server was started"""
        nbm = self.notebook_manager
        body = self.request.body.strip()
        format = self.get_argument('format', default='json')
        name = self.get_argument('name', default=None)
        if body:
            fname = nbm.save_new_notebook(body, notebook_path='/', name=name, format=format)
        else:
            fname = nbm.new_notebook(notebook_path='/')
        self.set_header('Location', nbm.notebook_dir + fname)
        model = nbm.notebook_model(fname)
        self.set_header('Location', '{0}api/notebooks/{1}'.format(self.base_project_url, fname))
        self.finish(jsonapi.dumps(model))

class NotebookHandler(IPythonHandler):

    SUPPORTED_METHODS = ('GET', 'PUT', 'PATCH', 'POST','DELETE')

    @web.authenticated
    def get(self, notebook_path):
        """get checks if a notebook is not named, an returns a list of notebooks
        in the notebook path given. If a name is given, return 
        the notebook representation"""
        nbm = self.notebook_manager
        name, path = nbm.named_notebook_path(notebook_path)
        
        # Check to see if a notebook name was given
        if name is None:
            # List notebooks in 'notebook_path'
            notebooks = nbm.list_notebooks(path)
            self.finish(jsonapi.dumps(notebooks))
        else:
            # get and return notebook representation
            format = self.get_argument('format', default='json')
            download = self.get_argument('download', default='False')
            model = nbm.notebook_model(name, path)
            last_mod, representation, name = nbm.get_notebook(name, path, format)
            self.set_header('Last-Modified', last_mod)
            
            if download == 'True':
                if format == u'json':
                    self.set_header('Content-Type', 'application/json')
                    self.set_header('Content-Disposition','attachment; filename="%s.ipynb"' % name)
                    self.finish(representation)
                elif format == u'py':
                    self.set_header('Content-Type', 'application/x-python')
                    self.set_header('Content-Disposition','attachment; filename="%s.py"' % name)
                    self.finish(representation)
            else:
                self.finish(jsonapi.dumps(model))

    @web.authenticated
    def patch(self, notebook_path):
        """patch is currently used strictly for notebook renaming.
        Changes the notebook name to the name given in data."""
        nbm = self.notebook_manager
        name, path = nbm.named_notebook_path(notebook_path)
        data = jsonapi.loads(self.request.body)
        model = nbm.change_notebook(data, name, path)
        self.finish(jsonapi.dumps(model))

    @web.authenticated
    def post(self,notebook_path):
        """Create a new notebook in the location given by 'notebook_path'."""
        nbm = self.notebook_manager
        fname, path = nbm.named_notebook_path(notebook_path)
        body = self.request.body.strip()
        format = self.get_argument('format', default='json')
        name = self.get_argument('name', default=None)
        if body:
            fname = nbm.save_new_notebook(body, notebook_path=path, name=name, format=format)
        else:
            fname = nbm.new_notebook(notebook_path=path)
        self.set_header('Location', nbm.notebook_dir + path + fname)
        model = nbm.notebook_model(fname, path)
        self.finish(jsonapi.dumps(model))

    @web.authenticated
    def put(self, notebook_path):
        """saves the notebook in the location given by 'notebook_path'."""
        nbm = self.notebook_manager
        name, path = nbm.named_notebook_path(notebook_path)
        format = self.get_argument('format', default='json')
        nbm.save_notebook(self.request.body, notebook_path=path, name=name, format=format)
        model = nbm.notebook_model(name, path)
        self.set_status(204)
        self.finish(jsonapi.dumps(model))

    @web.authenticated
    def delete(self, notebook_path):
        """delete rmoves the notebook in the given notebook path"""
        nbm = self.notebook_manager
        name, path = nbm.named_notebook_path(notebook_path)
        nbm.delete_notebook(name, path)
        self.set_status(204)
        self.finish()


class NotebookCheckpointsHandler(IPythonHandler):
    
    SUPPORTED_METHODS = ('GET', 'POST')
    
    @web.authenticated
    def get(self, notebook_path):
        """get lists checkpoints for a notebook"""
        nbm = self.notebook_manager
        name, path = nbm.named_notebook_path(notebook_path)
        checkpoints = nbm.list_checkpoints(name, path)
        data = jsonapi.dumps(checkpoints, default=date_default)
        self.finish(data)
    
    @web.authenticated
    def post(self, notebook_path):
        """post creates a new checkpoint"""
        nbm = self.notebook_manager
        name, path = nbm.named_notebook_path(notebook_path)
        checkpoint = nbm.create_checkpoint(name, path)
        data = jsonapi.dumps(checkpoint, default=date_default)
        if path == None:
            self.set_header('Location', '{0}notebooks/{1}/checkpoints/{2}'.format(
                self.base_project_url, name, checkpoint['checkpoint_id']
                ))
        else:
            self.set_header('Location', '{0}notebooks/{1}/{2}/checkpoints/{3}'.format(
                self.base_project_url, path, name, checkpoint['checkpoint_id']
                ))
        self.finish(data)


class ModifyNotebookCheckpointsHandler(IPythonHandler):
    
    SUPPORTED_METHODS = ('POST', 'DELETE')
    
    @web.authenticated
    def post(self, notebook_path, checkpoint_id):
        """post restores a notebook from a checkpoint"""
        nbm = self.notebook_manager
        name, path = nbm.named_notebook_path(notebook_path)
        nbm.restore_checkpoint(name, checkpoint_id, path)
        self.set_status(204)
        self.finish()
    
    @web.authenticated
    def delete(self, notebook_path, checkpoint_id):
        """delete clears a checkpoint for a given notebook"""
        nbm = self.notebook_manager
        name, path = nbm.named_notebook_path(notebook_path)
        nbm.delete_checkpoint(name, checkpoint_id, path)
        self.set_status(204)
        self.finish()
        
#-----------------------------------------------------------------------------
# URL to handler mappings
#-----------------------------------------------------------------------------


_notebook_path_regex = r"(?P<notebook_path>.+)"
_checkpoint_id_regex = r"(?P<checkpoint_id>[\w-]+)"

default_handlers = [
    (r"api/notebooks/%s/checkpoints" % _notebook_path_regex, NotebookCheckpointsHandler),
    (r"api/notebooks/%s/checkpoints/%s" % (_notebook_path_regex, _checkpoint_id_regex),
        ModifyNotebookCheckpointsHandler),
    (r"api/notebooks/%s/" % _notebook_path_regex, NotebookHandler), 
    (r"api/notebooks/%s" % _notebook_path_regex, NotebookHandler),
    (r"api/notebooks/", NotebookRootHandler),
    (r"api/notebooks", NotebookRootHandler),
]




