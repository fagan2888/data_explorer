import base64
import io

from util import *

import plotly.graph_objs as go
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt
from dash.dependencies import Input, Output, State

import pandas as pd
import numpy as np


class AppObject(object):
    def __init__(self):
        self.df = None
        self.df_view = None

        self.numeric_cols = None
        self.categorical_cols = None
        self.ordinal_cols = None

        self.scatter_x, self.scatter_y = None, None

        self.app = dash.Dash()
        self.app.config['suppress_callback_exceptions'] = True
        self._set_default_layout()

        self.app.run_server()

    def _set_default_layout(self):
        self.app.layout = html.Div([
            html.Div(
                dcc.Upload(id='upload-data',
                           children=html.Div(['Drag and Drop or ', html.A('Select file')
            ]), style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            }, multiple=False)),
            html.Details([html.Summary('DataFrame Preview'),
                          html.Div(id='output-data-upload'),
                          html.Div(
                              dt.DataTable(rows=[{}]), style={'display': 'none'})
                          ]),
            html.Div(
                [html.Div(children=['Initializing...'], id='main-app', style={'display': 'inline-block', 'width': '49%'}),
                 html.Div(children=['Placeholder...'], style={'display': 'inline-block', 'width': '49%', 'float': 'right'})]),

        ])

        self.app.css.append_css({
            'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
        })

        @self.app.callback(Output('output-data-upload', 'children'),
                           [Input('upload-data', 'contents')])
        def update_df(contents):
            if contents is not None:
                children = self._parse_csv(contents)
                return [children]

        @self.app.callback(Output('main-app', 'children'),
                           [Input('output-data-upload', 'children')])
        def generate_app(_x):
            if self.df is not None:
                self.numeric_cols = list(filter(
                    lambda x: self.df[x].dtype == 'float64', self.df.columns
                ))
                self.categorical_cols = list(filter(
                    lambda x: self.df[x].dtype == 'object', self.df.columns
                ))
                self.ordinal_cols = list(filter(
                    lambda x: self.df[x].dtype == 'int64', self.df.columns
                ))
                print(self.numeric_cols)
                return [html.H2('Correlations Heatmap'),
                        self._make_heatmap(),
                        html.H2('Scatter plot'),
                        html.Div([
                            html.Div([
                                html.Div(self._make_scatter_controls('xaxis'),
                                         style={'width': '49%', 'display': 'inline-block'}),  # TODO column dropdown
                                html.Div(self._make_scatter_controls('yaxis'),
                                         style={'width': '49%', 'display': 'inline-block', 'float': 'right'})
                                # TODO scale
                            ], id='scale-controls'),  # scale controls
                            html.Div([
                                html.Div([
                                    html.H6('Color by'),
                                    dcc.Dropdown(
                                        id='scatter-color',
                                        options=[{'label': '', 'value': ''}] +
                                                [{'label': i, 'value': i}
                                                for i in
                                                (self.categorical_cols + self.ordinal_cols)
                                                if self.df[i].nunique() < 15],
                                        value=''
                                    )
                                ], style={'width': '49%', 'display': 'inline-block'}),
                                html.Div([
                                    html.H6('Bubble Size'),
                                    dcc.Dropdown(
                                        id='scatter-size',
                                        options=[{'label': '', 'value': ''}] + [{'label': i, 'value': i}
                                                                                for i in self.numeric_cols],
                                        value=''
                                    )
                                ], style={'width': '49%', 'display': 'inline-block', 'float': 'right'})
                            ], id='color-size-controls')  # size and color controls
                        ]),
                        html.Div(id='more-plots')]

        @self.app.callback(Output('xaxis-column', 'value'),
                           [Input('heatmap', 'clickData')])
        def change_xcol(clickData):
            if clickData is not None:
                x_col = clickData['points'][0]['x']
                self.scatter_x = x_col
                return x_col
            return ''

        @self.app.callback(Output('yaxis-column', 'value'),
                           [Input('heatmap', 'clickData')])
        def change_xcol(clickData):
            if clickData is not None:
                y_col = clickData['points'][0]['y']
                self.scatter_x = y_col
                return y_col
            return ''

        #@self.app.callback(Output('more-plots', 'children'),
        #                   [Input('heatmap', 'clickData')])
        @self.app.callback(Output('more-plots', 'children'),
                           [Input('xaxis-column', 'value'),
                            Input('yaxis-column', 'value'),
                            Input('xaxis-type', 'value'),
                            Input('yaxis-type', 'value'),
                            Input('scatter-color', 'value'),
                            Input('scatter-size', 'value')])
        def display_hm_click(x_col, y_col, xlog, ylog, colorcol, sizecol):
            if x_col != '' and y_col != '':
                self.scatter_x, self.scatter_y = x_col, y_col

                return [
                    html.Div(self._make_scatterplot(x_col, y_col, xlog, ylog, colorcol, sizecol),
                             style={'width': '59%', 'display': 'inline-block'}),
                    html.Div([
                        html.Div(self._make_histogram(x_col, 'hist-1'), style={ 'height': '48%'}),
                        html.Div(self._make_histogram(y_col, 'hist-2'), style={ 'height': '48%'})
                    ], style={'width': '39%', 'float': 'right', 'display': 'inline-block'})
                ]



    def _make_scatter_controls(self, name):
        return [html.H6(name),
                dcc.Dropdown(
                    id='{}-column'.format(name),
                    options=[{'label': '', 'value': ''}] + [{'label': i, 'value': i}
                             for i in self.numeric_cols],
                    value=''
                ),
                dcc.RadioItems(
                    id='{}-type'.format(name),
                    options=[{'label': i, 'value': i} for i in ['Linear', 'Log']],
                    value='Linear',
                    labelStyle={'display': 'inline-block'}
                )]

    def _make_heatmap(self):
        return dcc.Graph(id='heatmap',
                                  figure={
                                      'data': [{
                                          'z': self.df[self.numeric_cols].corr().values[:,::-1].tolist(),
                                          'x': self.numeric_cols,
                                          'y': self.numeric_cols[::-1],
                                          'type': 'heatmap'
                                      }],
                                      'layout': go.Layout(
                                          height=500,
                                          margin=go.layout.Margin(t=50)
                                      )
                                  })

    def _make_scatterplot(self, xcol, ycol, xlog='Linear', ylog='Linear', colorcol='', sizecol=''):
        cols = [xcol, ycol]
        if sizecol != '':
            cols.append(sizecol)
        if colorcol != '':
            cols.append(colorcol)

        data = self._get_df()[cols].dropna()

        if colorcol == '':
            scatter_data = [
                                  go.Scattergl(
                                      x =  data[xcol],
                                      y = data[ycol],
                                      mode = 'markers',
                                      opacity= 0.5,
                                      marker = {
                                          'size': 10 if sizecol=='' else data[sizecol],
                                          'sizemode': 'area',
                                          'sizeref': 1 if sizecol=='' else 2.*max(data[sizecol]/40**2),
                                          'sizemin': 2
                                      },
                                      text='' if sizecol == '' else data[sizecol]
                                  )
                              ]
        else:
            scatter_data = [
                                  go.Scattergl(
                                      x =  data[data[colorcol] == i][xcol],
                                      y = data[data[colorcol] == i][ycol],
                                      mode = 'markers',
                                      opacity= 0.3,
                                      marker = {
                                          'size': 10 if sizecol=='' else data[sizecol],
                                          'sizemode': 'area',
                                          'sizeref': 1 if sizecol=='' else 2.*max(data[sizecol]/40**2),
                                          'sizemin': 2
                                      },
                                      name=str(i)
                                  ) for i in data[colorcol].unique()
                              ]

        return dcc.Graph(id='scatter-plot',
                          figure={
                              'data':scatter_data,
                              'layout': go.Layout(
                                  xaxis = { 'title': xcol, 'type': xlog.lower() },
                                  yaxis = { 'title': ycol, 'type': ylog.lower() },
                                  height=500,
                                  margin=go.layout.Margin(
                                      l=50, r=0, b=50, t=0
                                  )
                              )
                          })

    def _make_histogram(self, col, name, logscale=False):
        data = self._get_df()[col]
        if logscale:
            data = np.log(data[data > 0])

        histogram = dcc.Graph(id=name,
                         figure={
                             'data': [
                                 go.Histogram(x=data)
                             ],
                             'layout': go.Layout(
                                 xaxis = { 'title': col if not logscale else 'log({})'.format(col)},
                                 height=150,
                                  margin=go.layout.Margin(
                                      l=30, r=0, b=50, t=0
                                  )
                             )
                         })

        box_plot = dcc.Graph(id=name+'_box',
                             figure={
                                 'data': [
                                     go.Box(x=data, boxmean='sd') ],
                                 'layout': go.Layout(
                                     height=100,
                                     margin=go.layout.Margin(
                                         l=30, r=0, b=0, t=0
                                     )
                                 )
                             })

        return [histogram, box_plot]

    def _parse_csv(self, contents: str):
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        try:
            self.df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        except Exception as e:
            print(e)
            return html.Div(['There was an error processing the file'])

        return html.Div([dt.DataTable(rows=self.df.head(20).to_dict('records'))]
        )

    def _get_df(self):
        if self.df is None and self.df_view is None:
            raise Exception('df not loaded')
        if self.df_view is not None:
            return self.df_view
        else:
            return self.df

    def _filter_df(self, *conds):
        try:
            self.df_view = self.df.query(' and '.join(conds))
        except:
            raise Exception('Filter failed')
        if len(self.df_view) == 0:
            self.df_view = None
            raise Exception('Filter returned 0  rows')