"""A web application to translate color schemes between dark- and light-background."""

from functools import partial

import flask
import numpy as np
from werkzeug.exceptions import (HTTP_STATUS_CODES,
                                 HTTPException, InternalServerError, TooManyRequests)

import cam
from color_io import color_to_decimal, color_to_hex, color_to_int, parse_color

app = flask.Flask(__name__)


@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(429)
@app.errorhandler(500)
def handle_error(err):
    """Renders an error page in the site style."""
    if isinstance(err, HTTPException):
        code, desc = err.code, err.description
    else:
        code, desc = 500, '%s: %s' % (err.__class__.__name__, err)
    context = dict(code=code, reason=HTTP_STATUS_CODES[code], message=desc)
    return flask.render_template('error.html', **context), code


@app.route('/')
def index():
    """Renders the main UI page."""
    return flask.render_template('index.html')


@app.route('/result', methods=['POST'])
def result():
    """Renders the result page."""
    form = flask.request.form

    J_factor, M_factor = float(form['J_factor']), float(form['M_factor'])

    if form['direction'] == 'to_dark':
        translate_fn = partial(cam.translate, cond_src=cam.LIGHT_BG, cond_dst=cam.DARK_BG)
        left_bg, right_bg = '#fff', '#000'
    elif form['direction'] == 'to_light':
        translate_fn = partial(cam.translate, cond_src=cam.DARK_BG, cond_dst=cam.LIGHT_BG)
        left_bg, right_bg = '#000', '#fff'
    else:
        raise InternalServerError('Translation direction not specified.')
    translate_fn = partial(translate_fn, J_factor=J_factor, M_factor=M_factor)

    inputs_txt, inputs, outputs_txt = [], [], []
    for color in form['colors'].split('\n'):
        if not color.strip():
            continue
        try:
            inputs_txt.append(color)
            if len(inputs_txt) > 256:
                raise TooManyRequests('Limit 256 colors per request.')
            rgb_src = parse_color(color)
        except ValueError as err:
            raise InternalServerError(str(err))
        inputs.append(rgb_src)

    if not inputs:
        raise InternalServerError('At least one valid color is required.')
    inputs_arr = np.stack(inputs)
    outputs_arr = np.atleast_2d(translate_fn(inputs_arr))

    dump = ''
    csv = 'r_src,g_src,b_src,r_dst,g_dst,b_dst\n'
    for i, color in enumerate(inputs_txt):
        csv += '%d,%d,%d,' % color_to_int(inputs_arr[i])
        csv += '%d,%d,%d\n' % color_to_int(outputs_arr[i])
        if color.count(','):
            outputs_txt.append((color_to_decimal(inputs_arr[i]), color_to_decimal(outputs_arr[i])))
            dump += color_to_decimal(outputs_arr[i]) + '\n'
        else:
            outputs_txt.append((color_to_hex(inputs_arr[i]), color_to_hex(outputs_arr[i])))
            dump += color_to_hex(outputs_arr[i]) + '\n'

    return flask.render_template('result.html',
                                 left_bg=left_bg, right_bg=right_bg, outputs=outputs_txt,
                                 text=dump, csv=csv)
