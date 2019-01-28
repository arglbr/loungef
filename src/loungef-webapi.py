#!/usr/bin/python3
"""
This module serves a small web api for LoungeFiles project.
Example requests:
* http://{host}:{port}/loungef-api/files?status=available
* http://{host}:{port}/loungef-api/files/status=archived
"""
import urllib
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
dirsep   = '/' # TODO: Fix hardcoded directory separator.
env_path = Path(os.getenv("LF_APPHOME") + dirsep + 'config' + dirsep) / '.env'
load_dotenv(dotenv_path=env_path)

from flask import Flask, jsonify, abort, make_response, request
import pymongo

# FlaskApp
app = Flask(__name__)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}, 404))

@app.errorhandler(500)
def internal_error(error):
    return make_response(jsonify({'error': error.args[0]}, 500))

# loungef "business" method
def filterFiles(p_archived = False):
    """Method to find files under specific status.
    Receives a status that allow to show only archived files.
          :param property_id: Boolean to filter only the archived files. When False or not informed shows only the available files.
    """

    ret         = {}
    client      = pymongo.MongoClient(os.getenv("LF_MONGO_HOST"))
    db          = client[os.getenv("LF_MONGO_DB")]
    dirhistory  = db[os.getenv("LF_MONGO_CL")]
    logging.debug("Connection to MongoDB occurred successfuly.")

    filterdata  = {"archived": p_archived}
    cols_on_res = {"_id": 0, "inode": 1, "name": 1, 'path': 1, 'ctime': 1, 'mtime': 1, 'size': 1, 'archived': 1}
    results     = dirhistory.find(filterdata, cols_on_res).sort([("mtime", pymongo.ASCENDING)])

    for dh in results:
        ret.update({str(dh['inode']): dh})

    return ret

# REST Services
API_ROOT = '/loungef-api'

@app.route(API_ROOT + '/files/available', strict_slashes=False, methods=['GET'])
def getAvailableFiles():
    """Return only available files."""
    if len(request.args) == 0:
        # app.logger.info('GET available files.')
        flist = filterFiles()
        return jsonify(flist)
    else:
        # app.logger.error('This operation does not expect any parameter.')
        abort(500)

@app.route(API_ROOT + '/files/archived', strict_slashes=False, methods=['GET'])
def getArchivedFiles():
    """Return only archived files."""
    if len(request.args) == 0:
        # app.logger.info('GET available files.')
        flist = filterFiles(True)
        return jsonify(flist)
    else:
        # app.logger.error('This operations does not expect any parameter.')
        abort(500)

@app.route(API_ROOT + '/debugit', strict_slashes=False, methods=['GET'])
def debugIt():
    ret = {'client': os.getenv("LF_MONGO_HOST"),
            'db': os.getenv("LF_MONGO_DB"),
            'dirhistory': os.getenv("LF_MONGO_CL")}
    return jsonify(ret)


# Start app
if __name__ == '__main__':
    logging.basicConfig(filename=Path(os.getenv("LF_APILOGFILE")), format='%(asctime)s:%(levelname)s:%(message)s', level=logging.DEBUG)
    logging.info('Web-API started!')
    logging.debug('Directory to log: %s', os.getenv("LF_APILOGFILE"))
    app.run()
