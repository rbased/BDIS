import dash
import dash_table
import os
import json
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
import dash_leaflet as dl
import dash_leaflet.express as dlx
from graphics import *
import pandas as pd
from dash_extensions.javascript import Namespace, arrow_function
from dash.exceptions import PreventUpdate
import numpy as np
from geojson_utils import centroid
from addnl_details import *
from datetime import datetime
from encryptdecrypt import *
from loghandler import *
import flask
from flask import jsonify, request
from flask_talisman import Talisman
from glob import glob
import random
import base64

comfortaa_font = 'https://fonts.googleapis.com/css2?family=Comfortaa&family=Tajawal&display=swap'
FONT_AWESOME = "https://use.fontawesome.com/releases/v5.7.2/css/all.css"

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, comfortaa_font, FONT_AWESOME], update_title=None, suppress_callback_exceptions=True)
app.title = 'Bihar Digital Information System'
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True
server = app.server
ns = Namespace("dashExtensions", "default")


session_timeout_interval = 20  #In minutes

#---------------File Associations----------------------------------------------------------------------------------------------------------------
#Set root_dir for the app
if(os.path.exists('/home/siidcul/ukdis')):
    root_dir = '/home/siidcul/ukdis'
else:
    root_dir = os.getcwd()

#Basemap List path
basemap_list_path = os.path.join(root_dir, 'support_files', 'basemap_list.csv')

#Utarakhand District adn Park Boundary JSON file path
uk_dist_json_path = os.path.join(root_dir, 'json', 'Bihar_District.geojson')
parkbound_json_path = os.path.join(root_dir, 'json', 'parkbounds.geojson')

#Area list and dictionaries
area_list_file_path = os.path.join(root_dir, 'support_files', 'area_list.csv')
area_list_df = pd.read_csv(area_list_file_path)
district_dict = [{'label': x, 'value': x} for x in area_list_df['district'].unique()]

#PArk Names and Positions List CSV File
park_names_pos_csv_path = os.path.join(root_dir, 'support_files', 'park_names_position.csv')

#Park details file
park_details_file_path = os.path.join(root_dir, 'support_files', 'park_details.xlsx')
park_pos_df = pd.read_excel(park_details_file_path, engine = 'openpyxl')
park_selector_options = [{'label': x, 'value': '{}_{}_{}'.format(lat, lon, x)} for x,lat,lon in zip(park_pos_df['Industrial Estate Name'].values, park_pos_df['Latitude'].values, park_pos_df['Longitude'].values)]
park_marker_features = [{'type': 'Feature', 'geometry': {'type': 'Point',
                                  'coordinates': [park_pos_df['Longitude'].values[i], park_pos_df['Latitude'].values[i]]},
                      'properties': {'tooltip': park_pos_df['Industrial Estate Name'].values[i]}} for i in range(len(park_pos_df))]
park_json = {"type": "FeatureCollection", 'features': park_marker_features}

#Plots JSON file and details file path
plot_json_path = os.path.join(root_dir, 'json', 'plot.geojson')
plot_details_path = os.path.join(root_dir, 'support_files', 'plot_details.xlsx')
with open(plot_json_path) as f:
    plot_json = json.load(f)


#Additional Layers folder path
# addnl_layers_path = os.path.join(root_dir, 'additional_layers')

# with open(os.path.join(addnl_layers_path, 'roads.geojson')) as f:
#     road_json = json.load(f)
# with open(os.path.join(addnl_layers_path, '33kv.geojson')) as f:
#     kv33_json = json.load(f)
# with open(os.path.join(addnl_layers_path, 'bridge.geojson')) as f:
#     bridge_json = json.load(f)
# with open(os.path.join(addnl_layers_path, 'compline.geojson')) as f:
#     comp_json = json.load(f)
# with open(os.path.join(addnl_layers_path, '11kv.geojson')) as f:
#     kv11_json = json.load(f)
# with open(os.path.join(addnl_layers_path, 'elines.geojson')) as f:
#     elines_json = json.load(f)
# with open(os.path.join(addnl_layers_path, 'misc.geojson')) as f:
#     misc_json = json.load(f)
# with open(os.path.join(addnl_layers_path, 'vegetation.geojson')) as f:
#     veg_json = json.load(f)
with open(plot_json_path) as f:
    plot_json1 = json.load(f)

# epole_df = pd.read_csv(os.path.join(addnl_layers_path, 'epole.csv'))
# epole_markers = [dl.CircleMarker(center = [epole_df['lat'].values[i], epole_df['lon'].values[i]], radius = 3, pane = 'markerPane', color = '#29bf23', fillOpacity = 1) for i in range(len(epole_df))]

# manhole_df = pd.read_csv(os.path.join(addnl_layers_path, 'manhole.csv'))
# manhole_markers = [dl.CircleMarker(center = [manhole_df['lat'].values[i], manhole_df['lon'].values[i]], radius = 3, pane = 'markerPane', color = '#d874be', fillOpacity = 1) for i in range(len(manhole_df))]

# label_df = pd.read_csv(os.path.join(addnl_layers_path, 'label.csv'))
# label_markers = [dl.CircleMarker(center = [label_df['lat'].values[i], label_df['lon'].values[i]], radius = 3, pane = 'markerPane', color = '#262a61', fillOpacity = 1) for i in range(len(label_df))]

#User info file path
userinfo_path = os.path.join(root_dir, 'support_files', 'user_info.xlsx')
#----------------------------------------------------------------------------------------------------------

#-------------Global Variables----------------------------------------------------------------------------
is_logged_in = False
current_user_info = {'username': '', 'First Name': '', 'Last Name': ''}
filter_results_global_df = pd.DataFrame()
search_df = pd.DataFrame()
#---------------------------------------------------------------------------------------------------------

#-----------------Initial Processes------------------------------------------------------------------------
#Generate Basemaps list object for leaflet
basemap_list_df = pd.read_csv(basemap_list_path)
basemap_list_obj_for_leaftlet = [
                            dl.BaseLayer(dl.TileLayer(url = basemap_list_df['Path'].values[i],
                                                      attribution = '<a href = "http://www.rbasedservices.com/">RBased Services</a> | {}'.format(basemap_list_df['Title'].values[i])),
                                                      name = basemap_list_df['Title'].values[i],)
                            for i in range(1, len(basemap_list_df))
                    ]
basemap_list_obj_for_leaftlet.append(dl.BaseLayer(dl.TileLayer(url = basemap_list_df['Path'].values[0],
                          attribution = '<a href = "http://www.rbasedservices.com/">RBased Services</a> | {}'.format(basemap_list_df['Title'].values[0])),
                          name = basemap_list_df['Title'].values[0], checked = True))

#----------------------------------------------------------------------------------------------------------

#----Function to generate html Table content from the dataframe-------------------------------------------
def table_from_df(df):
    table_header_cols = [html.Th(x) for x in df.columns]
    table_header =  [html.Thead(html.Tr(table_header_cols, className = 'table-header'))]

    table_body_rows = []

    for i in range(len(df)):
        tr = html.Tr([html.Td(df[x].values[i]) for x in df.columns])
        table_body_rows.append(tr)

    table_body = [html.Tbody(table_body_rows)]

    return dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True, className = 'details-table')

def vertical_table_from_df(df):
    table_body_rows = [html.Tr([html.Td(c, className = 'vert-table-header'), html.Td(df[c].values[0], id = 'vert-table-value')]) for c in df.columns]

    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_body, striped=True, bordered=True, hover=True, className = 'vert-details-table')

def generate_captcha():
    img_list = glob(os.path.join(root_dir, 'captcha', '*.png'))
    sel_img = random.choice(img_list)

    #Get base64 for the image
    with open(sel_img, "rb") as img_file:
        my_string = base64.b64encode(img_file.read())

    return my_string.decode('utf-8'), os.path.basename(sel_img).split('.')[0]


#---------------------------------------------------------------------------------------------------------

#--------Function to generate the navigation bar------------------------------------------------------------
def generate_linkbar(active_val, is_logged_in = False):
    buttons_list = [{'label': 'Home', 'href': '/', 'color': 'primary'},
                    {'label': 'Park Details', 'href': '/park', 'color': 'primary'},
                    {'label': 'Administrator', 'href': '/admin', 'color': 'primary'},
                    {'label': 'About', 'href': '/about', 'color': 'primary'},
                    {'label': 'Login', 'href': '/login', 'color': 'success'}]
    buttons_list_logged_in = [{'label': 'Home', 'href': '/', 'color': 'primary'},
                    {'label': 'Park Details', 'href': '/park', 'color': 'primary'},
                    {'label': 'Administrator', 'href': '/admin', 'color': 'primary'},
                    {'label': 'About', 'href': '/about', 'color': 'primary'},
                    {'label': 'User Details', 'href': '/user', 'color': 'info'},
                    {'label': 'Logout', 'href': '/logout', 'color': 'danger'},]
    if(is_logged_in == False):
        elements_list = []
        for i in buttons_list:
            if(i['label'] == active_val):
                i['color'] = 'warning'
            elements_list.append(dbc.Col(dcc.Link(dbc.Button(i['label'], color = i['color'], className = 'link-button'), href = i['href'], refresh = True)))
    else:
        elements_list = []
        for i in buttons_list_logged_in:
            if(i['label'] == active_val):
                i['color'] = 'warning'
            elements_list.append(dbc.Col(dcc.Link(dbc.Button(i['label'], color = i['color'], className = 'link-button'), href = i['href'], refresh = True)))


    return dbc.Row(elements_list, id = 'link-buttons-container', no_gutters=True,)

def authenticate_login(sin, sout):
    #sin and sout are data dicts from dcc.Store()
    if sout is None and sin is None:
        return False
    elif sout is None and sin is not None:
        if(sin['status'] == 1):
            return True
        else:
            return False
    elif sin is None:
        return False
    else:
        if(sin['status'] == 1):
            login_time = datetime(sin['Year'], sin['Month'], sin['Day'], sin['Hour'], sin['Minute'], sin['Second'])
            logout_time = datetime(sout['Year'], sout['Month'], sout['Day'], sout['Hour'], sout['Minute'], sout['Second'])
            if(login_time > logout_time):
                return True
            else:
                return False
        else:
            return False
#-------------------------------------------------------------------------------------------------------------------------------------

#----Dash DataTable Properties-----------------------------------------------------------------------------------------------
style_table = {'height': '90vh', 'width': '94vw'}
style_header={'backgroundColor': '#2c3e50',
              'fontWeight': 'bold',
              'font-family':'sans-serif',
              'font-size': 'small',
              'color': 'white'}

style_cell={'height': 'auto',
            'minWidth': '180px',
            'width': '180px',
            'maxWidth': '180px',
            'whiteSpace': 'normal',
            'textAlign': 'left',
            'font-family':'sans-serif',
            'font-size': 'small'}

style_data_conditional=[{'if': {'row_index': 'odd'},'backgroundColor': 'rgb(248, 248, 248)'},
                        {"if": {"state": "selected"}, "backgroundColor": "#D4F1F4", "border": "1px solid black"},
                        {'if': {'column_id': 'Property'},"backgroundColor": "#2c3e50", 'fontWeight': 'bold',
                                                        'font-family':'sans-serif', 'font-size': 'small', 'color': 'white'}]

#-------------------------------------------------------------------------------------------------------------------------

heading_navbar = html.Div(html.P('Bihar Digital Information System', id = 'main-header'), id = 'heading-navbar')

rbs_logo_container = html.A(html.Img(src = rbs_logo, id = 'rbs-logo'), href = 'http://www.rbasedservices.com/')
giz_logo_container = html.A(html.Img(src = giz_logo, id = 'giz-logo'), href = 'https://www.giz.de/en/worldwide/368.html')
ukpcb_logo_container = html.A(html.Img(src = ukpcb_logo, id = 'ukpcb-logo'), href = 'https://ueppcb.uk.gov.in/')
siidcul_logo_container = html.A(html.Img(src = siidcul_logo, id = 'siidcul-logo'), href = 'https://www.biadabihar.in/')

links_navbar = html.Div(id = 'link-navbar')


main_content = html.Div([
                        html.Img(src = loading_image, id = 'loading-image')
                    ], id = 'main-content')


app.layout = html.Div([

                heading_navbar, links_navbar, siidcul_logo_container, giz_logo_container, rbs_logo_container,
                dcc.Store(id='store-login-uk', storage_type='local'),
                dcc.Store(id='store-logout-uk', storage_type='local'),
                dcc.Interval(id='session-interval-control', interval = 2000*60, n_intervals = 0),
                main_content, dcc.Location(id='url', refresh=False),
                dbc.Tooltip('R Based Services Pvt. Ltd.', target = 'rbs-logo'),
                dbc.Tooltip('Deutsche Gesellschaft fÃ¼r Internationale Zusammenarbeit - India', target = 'giz-logo'),
                dbc.Tooltip('Uttarakhand Pollution Control Board', target = 'ukpcb-logo'),
                dbc.Tooltip('Bihar Industrial Area Development Authority (BIADA)', target = 'siidcul-logo'),
                ], id = 'main-container')

#Generate the link navbar immediately and let the main content load later
@app.callback(Output('link-navbar', 'children'), [Input('url', 'pathname')], [State('store-login-uk', 'data'), State('store-logout-uk', 'data')])
def link_bar_generation(url, sin, sout):
    is_logged_in = authenticate_login(sin, sout)
    if(url == '/'):
        return generate_linkbar('Home', is_logged_in)
    elif(url == '/park'):
        return generate_linkbar('Park Details', is_logged_in)
    elif(url == '/admin' or url == '/plotdata' or url == '/parkdata' or url == '/editplot' or url == '/editpark'):
        return generate_linkbar('Administrator', is_logged_in)
    elif(url == '/login'):
        return generate_linkbar('Login', is_logged_in)
    elif(url == '/user'):
        return generate_linkbar('User Details', is_logged_in)
    elif(url == '/logout'):
        return generate_linkbar('Logout', True)
    elif(url == '/about'):
        return generate_linkbar('About', is_logged_in)
    else:
        return generate_linkbar('None', is_logged_in)



@app.callback(Output('main-content', 'children'), [Input('url', 'pathname'), Input('url', 'search')], [State('store-login-uk', 'data'), State('store-logout-uk', 'data')])
def navigate(url, search, sin, sout):
    is_logged_in = authenticate_login(sin, sout)
    if(url == '/'):

        with open(uk_dist_json_path) as uk_dis_f:
            uk_dis_json_leaflet = json.load(uk_dis_f)
        with open(plot_json_path) as f:
            plot_json = json.load(f)
        with open(parkbound_json_path) as park_f:
            park_json_leaflet = json.load(park_f)

        plot_df = pd.read_excel(plot_details_path, engine = 'openpyxl')
        df_for_ddown = plot_df[plot_df['Plot Number'] != '-']
        industry_ddown_options = [{'label': x, 'value': y} for x,y in zip(df_for_ddown['Plot Number'], df_for_ddown['UID'])]

        #For faster filtering in terms of district, park, sector and ID, the df is separated
        global search_df
        search_df = plot_df[['UID', 'Name of Industrial Estate', 'District', 'Name of allootte Unit', 'Sector', 'Plot Number']]


        #Generate tooltip for the Plot JSON
        for f in plot_json['features']:
            mini_df = plot_df[plot_df['UID'] == f['properties']['UID']]

            if(len(mini_df) > 0):
                format_plot_status = mini_df['Plot Status '].values[0]

                format_plot_no = mini_df['Plot Number'].values[0]
                format_ind_est = mini_df['Name of Industrial Estate'].values[0]
                format_all_unit = mini_df['Name of allootte Unit'].values[0]
                format_area = mini_df['Geometric Area (in Sq. Mtr.)'].values[0]
                format_sector = mini_df['Sector'].values[0]

                f['properties']['PCB'] = mini_df['Plot Status '].values[0]

                if(format_plot_status == 'Vacant'):
                    f['properties']['tooltip'] = r"<font size = 3><b>Plot No.: {}</b></font><br />Sector No.: {}<br />Industrial Estate: {}<br />Area: {} m<sup>2</sup><br />Plot status: <font color = 'red'><b>{}</b></font>".format(format_plot_no, format_sector, format_ind_est, format_area, format_plot_status)
                    f['properties']['name'] = 'Vacant'
                elif(format_plot_status == 'Alloted'):
                    f['properties']['tooltip'] = r"<font size = 3><b>Plot No.: {}</b></font><br />Sector No.: {}<br  />Industrial Estate: {}<br />Allootte Unit: {}<br />Area: {} m<sup>2</sup><br />Plot status: <font color = 'green'><b>{}</b></font>".format(format_plot_no, format_sector, format_ind_est, format_all_unit, format_area, format_plot_status)
                    f['properties']['name'] = format_all_unit
                else:
                    f['properties']['tooltip'] = r"<font size = 3><b>Plot No.: {}</b></font><br />Sector No.: {}<br  />Industrial Estate: {}<br />Allootte Unit: {}<br />Area: {} m<sup>2</sup><br />Plot status: <font color = 'orange'><b>{}</b></font>".format(format_plot_no, format_sector, format_ind_est, format_all_unit, format_area, format_plot_status)
                    f['properties']['name'] = format_all_unit

            else:
                f['properties']['tooltip'] = r'<b>No data available.</b>'
                f['properties']['name'] = 'No Data Available'
                f['properties']['PCB'] = 'N.A'

        choropleth_color_scheme = pd.read_csv(os.path.join(root_dir, 'support_files', 'choropleth_color_scheme.csv'))
        classes = choropleth_color_scheme['Class'].values
        colorscale = choropleth_color_scheme['Color'].values
        style = dict(weight=1, opacity=0.8, color = 'black', fillOpacity=1)

        plot_caption = '<b>Plot Status</b><br />'
        for pp in range(len(classes) - 1):
            if(pp == (len(classes) - 2)):
                plot_caption = plot_caption + '<font style = "margin-right: 10px; margin-left: 5px; border: 1px solid black; background-color: {}; font-size: xx-small"><b>&emsp;</b></font>{}'.format(colorscale[pp], classes[pp])
            else:
                plot_caption = plot_caption + '<font style = "margin-right: 10px; margin-left: 5px; border: 1px solid black; background-color: {}; font-size: xx-small"><b>&emsp;</b></font>{}<br />'.format(colorscale[pp], classes[pp])


        overlay_list_obj_for_leaflet = [dl.Overlay(dl.GeoJSON(data=uk_dis_json_leaflet,
                                                              options = dict(style=dict(weight=3, opacity=1, color='#FF0000', fillOpacity=0))),
                                                              name = '<font style = "margin-right: 10px; margin-left: 5px; border: 2px solid #FF0000; font-size: xx-small"><b>&emsp;</b></font>District',
                                                              checked = True),
                                        dl.Overlay(dl.LayerGroup(id = 'plots_label'), name="  Plot Number", checked=0),
                                        dl.Overlay(dl.GeoJSON(data=plot_json, id = 'plot-json',
                                                              options = dict(style=ns("function0")),
                                                              hideout=dict(colorscale=colorscale, classes=classes, style=style, colorProp="PCB"),
                                                              ),
                                                              name = plot_caption,
                                                              checked = True),
                                        dl.Overlay(dl.LayerGroup(id = 'selected-plot'),
                                                              name = '<font style = "margin-right: 10px; margin-left: 5px; border: 3px dashed #800080; font-size: xx-small"><b>&emsp;</b></font>Selected Plot',
                                                              checked = True),
                                        dl.Overlay(dl.LayerGroup(id = 'filter-results'),
                                                              name = '<font style = "margin-right: 10px; margin-left: 5px; border: 3px dashed #ff0000; font-size: xx-small"><b>&emsp;</b></font>Filter Results',
                                                              checked = True),
                                        dl.Overlay(dl.GeoJSON(data = park_json, id = 'park-markers', zoomToBoundsOnClick = True), name = 'Parks', checked = True),
                                        ]

        leaflet_map = dl.Map(dl.LayersControl(basemap_list_obj_for_leaftlet + overlay_list_obj_for_leaflet),
                                center = (25.726369, 85.887942), zoom = 8,
                                id = 'basic-leaflet-main-map', zoomControl = False, animate = True, trackResize = True)

        if(is_logged_in):
            d_but = dbc.Button(html.I(className = 'fas fa-download'), id = 'basic-table-header-download')
            e_but = dcc.Link(dbc.Button(html.I(className = 'fas fa-pencil-alt'), id = 'basic-table-header-edit'), href = '/editplot', target = '_blank', id = 'basic-edit-link')
            f_d_but = dbc.Button(html.I(className = 'fas fa-download'), id = 'basic-filter-header-download')
        else:
            d_but = dbc.Button(html.I(className = 'fas fa-download'), id = 'basic-table-header-download', style = {'display': 'none'})
            e_but = dcc.Link(dbc.Button(html.I(className = 'fas fa-pencil-alt'), id = 'basic-table-header-edit', style = {'display': 'none'}), href = '/editplot', target = '_blank', id = 'basic-edit-link')
            f_d_but = dbc.Button(html.I(className = 'fas fa-download'), id = 'basic-filter-header-download', style = {'display': 'none'})


        basic_table_content = [html.Div([
                                        html.P('Loading Data...', id = 'basic-table-header-text'),
                                        html.Div([e_but,
                                                d_but,
                                                dbc.Button(html.I(className = 'fas fa-times'), id = 'basic-table-header-close'),
                                                dbc.Tooltip('Hide Panel', target = 'basic-table-header-close'),
                                                dbc.Tooltip('Export Data', target = 'basic-table-header-download'),
                                                dbc.Tooltip('Edit Data', target = 'basic-table-header-edit'),
                                                dcc.Download(id="download-dataframe-xlsx")], id = 'basic-table-header-butt-grp')
                                    ], id = 'basic-table-header'),
                               dbc.Spinner(html.Div('Table Content', id = 'basic-table-content'), size = 'lg', color="success")]

        district_dict_from_plot_data = [{'label': x, 'value': x} for x in plot_df['District'].unique()]
        park_dict_from_plot_data = [{'label': x, 'value': x} for x in plot_df['Name of Industrial Estate'].unique()]
        park_type_from_plot_data = [{'label': x, 'value': x} for x in plot_df['Type of Plot'].unique()]


        search_bar_content = [html.Div(dbc.Button([html.I(className = 'fas fa-filter'), html.P('Adv Search', id = 'home-filter-caption')],id = 'query-toggle'), id = 'query-area-search-bar'),
                              html.Div([
                                    dcc.Dropdown(options = district_dict_from_plot_data, id = 'district-dropdown', placeholder = 'Select District'),
                                    dbc.Spinner(dcc.Dropdown(id = 'park-selector', placeholder = 'Select Park'), color = 'success', spinner_style={"width": "12px", "height": "12px"}),
                                    dbc.Spinner(dcc.Dropdown(id = 'sector-selector', placeholder = 'Select Sector'), color = 'info', spinner_style={"width": "12px", "height": "12px"}),
                                    dbc.Spinner(dcc.Dropdown(id = 'home-industry-dropdown', placeholder = 'Select Plot No'), color = 'danger', spinner_style={"width": "12px", "height": "12px"}),
                                  ], id = 'dropdown-area-search-bar'),
                              dbc.Tooltip('Toggle advanced query', target = 'query-toggle', placement = 'bottom'),
                              dbc.Modal([dbc.ModalHeader([html.P("Header",id = 'park-modal-header'), dbc.Button(html.I(className = 'fas fa-times'), className="ml-auto", id="close-park-modal",)], style = {'background': '#2c3e50'}),
                                        dbc.ModalBody(html.Img(src = loading_image, id = 'loading-image-modal'), id = 'park-modal-body'),
                                        ], id = 'park-modal', is_open = False, size="lg", scrollable=True, backdropClassName = 'park-modal-backdrop')]

        adv_query_content = [
                            dbc.CardHeader("Advanced Query", id = 'adv-query-heading'),
                            dbc.CardBody(
                                [

                                    html.P('Park/Industry', style = {'font-size': 'small', 'font-weight': 'bold'}),
                                    dcc.Dropdown(options = park_dict_from_plot_data,
                                                  value = [],id = 'plot-parkind-dropdown', multi = True, style = {'color': 'black', 'font-size': 'small'}),
                                    html.P(['Area (km', html.Sup('2'), ')'], style = {'font-size': 'small', 'font-weight': 'bold', 'margin-top': '15px'}),
                                    dcc.RangeSlider(id='area-range-slider', min=0, max=1000000, step=500, value=[0, 1000000], marks={x: {'label': str(x/1000000)} for x in range(0,1000001,200000)},),
                                    html.P('Selected Range : ', style = {'font-size': 'small', 'margin-top': '5px', 'text-align': 'center'}, id = 'area-range-value-display'),
                                    html.P('Plot Status', style = {'font-size': 'small', 'font-weight': 'bold'}),
                                    dcc.Dropdown(options = [{'label': x, 'value': x} for x in ['Allotted', 'Cancelled', 'Closed', 'Construction Stop', 'Construction not started', 'Litigated','Reserved', 'Under Consturction', 'Vacant', 'Working']],
                                                  value = [],id = 'plot-status-dropdown', multi = True, style = {'color': 'black', 'font-size': 'small'}),
                                    html.P('PCB Category', style = {'font-size': 'small', 'font-weight': 'bold', 'margin-top': '15px'}),
                                    dcc.Dropdown(options = [{'label': 'Green', 'value': 'Green'},
                                                            {'label': 'Orange', 'value': 'Orange'},
                                                            {'label': 'Red', 'value': 'RED'},
                                                            {'label': 'White', 'value': 'White'},
                                                            {'label': 'Plot Vacant', 'value': 'Plot Vacant'},
                                                            {'label': 'NA', 'value': 'N.A'},
                                                            ], value = [],id = 'pcb-category-dropdown', multi = True, style = {'color': 'black', 'font-size': 'small'}),
                                    html.P('Plot Type', style = {'font-size': 'small', 'font-weight': 'bold', 'margin-top': '15px'}),
                                    dcc.Dropdown(options = park_type_from_plot_data, value = [],id = 'plot-type-dropdown', multi = True, style = {'color': 'black', 'font-size': 'small'}),



                                ], id = 'adv-query-controls'),
                            dbc.CardFooter(dbc.Button("Apply filter", color="info", id = 'apply-filter-button'), id = 'adv-query-footer'),
                        ]

        filter_results_container_contents = [html.Div([
                                                html.P('Filter Results', id = 'basic-filter-header-text'),
                                                html.Div([f_d_but,
                                                        dbc.Button(html.I(className = 'fas fa-times'), id = 'basic-filter-header-close'),
                                                        dbc.Tooltip('Hide Panel', target = 'basic-filter-header-close'),
                                                        dbc.Tooltip('Export Data', target = 'basic-filter-header-download'),
                                                        dcc.Download(id="download-filtered-data-xlsx")], id = 'fil-res-but-grp')
                                            ], id = 'basic-filter-results-header'),
                                            dbc.Spinner(html.Div('Table Content', id = 'basic-filter-results-content'), size = 'lg', color="info")]

        main_content_basic_map = [html.Div([leaflet_map,
                                            html.Div(basic_table_content, id = 'basic-table-container')],
                                        id = 'basic-leaflet-map-container'),
                                  html.Div(filter_results_container_contents, id = 'basic-details-container'),
                                  html.Div('Display', id = 'viewport-overlay'),
                                  html.Div(search_bar_content, id = 'search-bar-overlay'),
                                  html.Div(dbc.Card(adv_query_content, color="primary", inverse=True, style = {'height': '100%'}, id = 'adv-query-card'), id = 'query-overlay')]

        return main_content_basic_map
    elif(url == '/park'):

        with open(uk_dist_json_path) as uk_dis_f:
            uk_dis_json_leaflet = json.load(uk_dis_f)

        with open(parkbound_json_path) as park_f:
            park_json_leaflet = json.load(park_f)

        #Park markers


        overlay_list_obj_for_leaflet = [dl.Overlay(dl.GeoJSON(data=uk_dis_json_leaflet,
                                                              options = dict(style=dict(weight=3, opacity=1, color='#FF0000', fillOpacity=0))),
                                                              name = '<font style = "margin-right: 10px; margin-left: 5px; border: 2px solid #FF0000; font-size: xx-small"><b>&emsp;</b></font>District',
                                                              checked = True),
                                        dl.Overlay(dl.GeoJSON(data = park_json, id = 'park-markers', zoomToBoundsOnClick = True), name = 'Parks', checked = True),
                                        dl.Overlay(dl.GeoJSON(data = plot_json1, options = {'style': {'color': '#0000FF', 'fillOpactiy': '0.6'}}),name='<font style = "margin-right: 10px; margin-left: 5px; border: 1px solid #0000FF; background-color: #0000FF; font-size: xx-small"><b>&emsp;</b></font>Plots', checked=1),
                                        ]

        leaflet_map = dl.Map(dl.LayersControl(basemap_list_obj_for_leaftlet + overlay_list_obj_for_leaflet),
                                center = (25.726369, 85.887942), zoom = 8,
                                id = 'park-leaflet-main-map', zoomControl = False, animate = True, trackResize = True)

        park_details_content = [html.Div([html.P('Park Details', id = 'park-filter-header-text'),
                                                dbc.Button(html.I(className = 'fas fa-times'), id = 'park-filter-header-close'),
                                                dbc.Tooltip('Hide Panel', target = 'park-filter-header-close'),
                                                dcc.Download(id="download-park-data-xlsx")
                                            ], id = 'park-results-header'),
                                            dbc.Spinner(html.Div('Table Content', id = 'park-details-panel'), size = 'lg', color="info")]

        park_content = [html.Div(leaflet_map, id = 'park-map-panel'),
                        html.Div(park_details_content, id = 'park-details-content'),
                        html.Div(dcc.Dropdown(id = 'park-marker-selector', placeholder = 'Select Park...', options = park_selector_options), id = 'park-search-panel')]
        return park_content
    elif(url == '/admin'):
        if(is_logged_in):

            data_df = pd.read_excel(plot_details_path, engine = 'openpyxl')
            parks_list = [{'value': i, 'label': i} for i in data_df['Name of Industrial Estate'].unique()]

            park_df = pd.read_excel(park_details_file_path, engine = 'openpyxl')
            park_list_options = [{'value': j, 'label': i} for i, j in zip(park_df['Industrial Estate Name'].values, park_df.index)]


            admin_content = html.Div([dbc.Alert('Welcome, Administrator'),
                                        html.Div([html.Div([html.Img(src = show_plot_data_img, id = 'edit-plot-data-div-img'),
                                                            html.P('Edit Plot Data', id = 'edit-plot-data-div-text'),
                                                            dcc.Dropdown(options = parks_list, placeholder = 'Select Park', id = 'edit-plot-data-div-dist'),
                                                            dbc.Spinner(dcc.Dropdown(placeholder = 'Select UID', id = 'edit-plot-data-div-uid'),spinner_style={"width": "6px", "height": "6px"}, color = 'danger'),
                                                            html.Div(dcc.Link(dbc.Button('Edit', id = 'edit-plot-data-div-button', color = 'success'), href = '/editplot', refresh = True), id = 'editplot-link')
                                                        ], id = 'edit-plot-data-div'),
                                                html.Div([html.Img(src = factory_icon, id = 'edit-park-data-div-img'),
                                                          html.P('Edit Park Data', id = 'edit-park-data-div-text'),
                                                          dcc.Dropdown(options = park_list_options, placeholder = 'Select Park', id = 'edit-park-data-div-dist'),
                                                          html.Div(dcc.Link(dbc.Button('Edit', id = 'edit-park-data-div-button', color = 'success'), href = '/editpark', refresh = True),id = 'editpark-link')
                                                ], id = 'show-plot-dataset-div'),], id = 'admin-plot'),
                                      html.Div([html.Div([html.Img(src = database_icon, id = 'edit-complete-plot-data-div-img'),
                                                          html.P('Show Plot Dataset', id = 'edit-complete-plot-data-div-text'),
                                                          dcc.Link(dbc.Button('Plot Dataset', id = 'edit-complete-plot-data-div-button', color = 'danger'), href = '/plotdata', refresh = True, style = {'width': '100%'})
                                                      ], id = 'edit-park-data-div'),
                                                html.Div([
                                                            html.Img(src = data_icon, id = 'edit-complete-park-data-div-img'),
                                                            html.P('Show Park Dataset', id = 'edit-complete-park-data-div-text'),
                                                            dcc.Link(dbc.Button('Park Dataset', id = 'edit-complete-park-data-div-button', color = 'danger'), href = '/parkdata', refresh = True, style = {'width': '100%'})
                                                        ], id = 'show-park-dataset-div'),], id = 'admin-park')
                                ], id = 'admin-logged-in-div')
        else:
            admin_content = html.Div([
                            html.Img(src = access_denied_logo, id = 'admin-not-logged-in-div-img'),
                            html.P('You are not logged in. Please log in to continue.', 'admin-not-logged-in-div-msg')
                        ], id = 'admin-not-logged-in-div')
        return admin_content
    elif(url == '/editplot'):
        style_table = {'height': '90vh', 'width': '94vw'}
        style_header={'backgroundColor': '#2c3e50',
                      'fontWeight': 'bold',
                      'font-family':'sans-serif',
                      'font-size': 'small',
                      'color': 'white'}

        style_cell={'height': 'auto',
                    'minWidth': '180px',
                    'width': '180px',
                    'maxWidth': '180px',
                    'whiteSpace': 'normal',
                    'textAlign': 'left',
                    'font-family':'sans-serif',
                    'font-size': 'small'}

        style_data_conditional=[{'if': {'row_index': 'odd'},'backgroundColor': 'rgb(248, 248, 248)'},
                                {"if": {"state": "selected"}, "backgroundColor": "#D4F1F4", "border": "1px solid black"},
                                {'if': {'column_id': 'Property'},"backgroundColor": "#2c3e50", 'fontWeight': 'bold',
                                                                'font-family':'sans-serif', 'font-size': 'small', 'color': 'white'}]
        if(is_logged_in):
            index = search.split('=')[1]
            data_df = pd.read_excel(plot_details_path, engine = 'openpyxl')
            mini_df = data_df[data_df.index == int(index)]

            mini_df_2_show = pd.DataFrame({'Property': mini_df.columns, 'Value': [mini_df[c].values[0] for c in mini_df.columns]})
            cols_list = []
            for i in mini_df_2_show.columns:
                if(i == 'Property'):
                    cols_list.append({'name': i, 'id': i, 'editable': False})
                else:
                    cols_list.append({'name': i, 'id': i, 'editable': True})
            datatable_content = dbc.Spinner(dash_table.DataTable(id = 'edit-plot-table',
                                      columns = cols_list,
                                      data = mini_df_2_show.to_dict('records'),
                                      style_table= style_table,
                                      fixed_rows = {'headers': True},
                                      style_header=style_header,
                                      style_cell= style_cell,
                                      style_data_conditional=style_data_conditional,
                                      editable=True, sort_action='native', filter_action='native'))

            display_title = '({}) {}'.format(mini_df['Plot Number'].values[0], mini_df['Name of allootte Unit'].values[0])

            plot_ds_comps = [html.Div([
                                        html.P('Edit Plot Data: {}'.format(display_title), id = 'edit-plot-details-header-text'),
                                        html.Div([
                                                    dbc.Button(html.I(className = 'fas fa-save'), id = 'edit-plot-save'),
                                                    dbc.Tooltip('Save Changes', target = 'edit-plot-save', placement = 'bottom'),
                                                    dcc.ConfirmDialog(id='edit-plot-confirm-save-changes',message='Save the changes to the dataset?'),

                                                ], id = 'edit-plot-header-buttons')
                                    ], id = 'edit-plot-details-header'),
                                dbc.Spinner(dbc.Alert('Changes saved successfully.', id = 'edit-plot-save-toast', dismissable=True, is_open= 1, duration=5000),spinner_style={"width": "20px", "height": "20px"}, color = 'success'),
                                html.Div(datatable_content, id = 'edit-plot-details-datatable'),

                            ]
            return html.Div(plot_ds_comps, id = 'plot-edit-dataset-container')
        else:
            admin_content = html.Div([
                            html.Img(src = access_denied_logo, id = 'admin-not-logged-in-div-img'),
                            html.P('You are not logged in. Please log in to continue.', 'admin-not-logged-in-div-msg')
                        ], id = 'admin-not-logged-in-div')
            return admin_content

    elif(url == '/editpark'):
        style_table = {'height': '90vh', 'width': '94vw'}
        style_header={'backgroundColor': '#2c3e50',
                      'fontWeight': 'bold',
                      'font-family':'sans-serif',
                      'font-size': 'small',
                      'color': 'white'}

        style_cell={'height': 'auto',
                    'minWidth': '180px',
                    'width': '180px',
                    'maxWidth': '180px',
                    'whiteSpace': 'normal',
                    'textAlign': 'left',
                    'font-family':'sans-serif',
                    'font-size': 'small'}

        style_data_conditional=[{'if': {'row_index': 'odd'},'backgroundColor': 'rgb(248, 248, 248)'},
                                {"if": {"state": "selected"}, "backgroundColor": "#D4F1F4", "border": "1px solid black"},
                                {'if': {'column_id': 'Property'},"backgroundColor": "#2c3e50", 'fontWeight': 'bold',
                                                                'font-family':'sans-serif', 'font-size': 'small', 'color': 'white'}]
        if(is_logged_in):
            index = search.split('=')[1]
            data_df = pd.read_excel(park_details_file_path, engine = 'openpyxl')
            mini_df = data_df[data_df.index == int(index)]

            mini_df_2_show = pd.DataFrame({'Property': mini_df.columns, 'Value': [mini_df[c].values[0] for c in mini_df.columns]})
            cols_list = []
            for i in mini_df_2_show.columns:
                if(i == 'Property'):
                    cols_list.append({'name': i, 'id': i, 'editable': False})
                else:
                    cols_list.append({'name': i, 'id': i, 'editable': True})
            datatable_content = dbc.Spinner(dash_table.DataTable(id = 'edit-park-table',
                                      columns = cols_list,
                                      data = mini_df_2_show.to_dict('records'),
                                      style_table= style_table,
                                      fixed_rows = {'headers': True},
                                      style_header=style_header,
                                      style_cell= style_cell,
                                      style_data_conditional=style_data_conditional,
                                      editable=True, sort_action='native', filter_action='native'))

            park_name = mini_df['Industrial Estate Name'].values[0]

            plot_ds_comps = [html.Div([
                                        html.P('Edit Park Data: {}'.format(park_name), id = 'edit-park-details-header-text'),
                                        html.Div([
                                                    dbc.Button(html.I(className = 'fas fa-save'), id = 'edit-park-save'),
                                                    dbc.Tooltip('Save Changes', target = 'edit-park-save', placement = 'bottom'),
                                                    dcc.ConfirmDialog(id='edit-park-confirm-save-changes',message='Save the changes to the dataset?'),

                                                ], id = 'edit-park-header-buttons')
                                    ], id = 'edit-park-details-header'),
                                dbc.Spinner(dbc.Alert('Changes saved successfully.', id = 'edit-park-save-toast', dismissable=True, is_open=False, duration=5000),spinner_style={"width": "20px", "height": "20px"}, color = 'success'),
                                html.Div(datatable_content, id = 'edit-park-details-datatable'),

                            ]
            return html.Div(plot_ds_comps, id = 'park-edit-dataset-container')
        else:
            admin_content = html.Div([
                            html.Img(src = access_denied_logo, id = 'admin-not-logged-in-div-img'),
                            html.P('You are not logged in. Please log in to continue.', 'admin-not-logged-in-div-msg')
                        ], id = 'admin-not-logged-in-div')
            return admin_content
    elif(url == '/plotdata'):
        style_table = {'height': '90vh', 'width': '94vw'}
        style_header={'backgroundColor': '#2c3e50',
                      'fontWeight': 'bold',
                      'font-family':'sans-serif',
                      'font-size': 'small',
                      'color': 'white'}

        style_cell={'height': 'auto',
                    'minWidth': '180px',
                    'width': '180px',
                    'maxWidth': '180px',
                    'whiteSpace': 'normal',
                    'textAlign': 'left',
                    'font-family':'sans-serif',
                    'font-size': 'small'}

        style_data_conditional=[{'if': {'row_index': 'odd'},'backgroundColor': 'rgb(248, 248, 248)'},
                                {"if": {"state": "selected"}, "backgroundColor": "#D4F1F4", "border": "1px solid black"},
                                {'if': {'column_id': 'Property'},"backgroundColor": "#2c3e50", 'fontWeight': 'bold',
                                                                'font-family':'sans-serif', 'font-size': 'small', 'color': 'white'}]

        if(is_logged_in):
            plot_df = pd.read_excel(plot_details_path, engine = 'openpyxl')

            datatable_content = dbc.Spinner(dash_table.DataTable(id = 'table',
                                      columns = [{'name': i, 'id': i} for i in plot_df.columns],
                                      data = plot_df.to_dict('records'),
                                      style_table= style_table,
                                      page_size = 30,
                                      fixed_rows = {'headers': True},
                                      style_header=style_header,
                                      style_cell= style_cell,
                                      style_data_conditional=style_data_conditional,
                                      editable=True, sort_action='native', filter_action='native'))

            plot_ds_comps = [html.Div([
                                        html.P('Plot Details', id = 'full-plot-details-header-text'),
                                        html.Div([
                                                    dbc.Button(html.I(className = 'fas fa-download'), id = 'full-plot-download'),
                                                    dbc.Button(html.I(className = 'fas fa-save'), id = 'full-plot-save'),
                                                    dbc.Tooltip('Export as Excel File', target = 'full-plot-download', placement = 'bottom'),
                                                    dbc.Tooltip('Save Changes', target = 'full-plot-save', placement = 'bottom'),
                                                    dcc.Download(id="download-full-plot-dataset"),
                                                    dcc.ConfirmDialog(id='full-plot-confirm-save-changes',message='Save the changes to the dataset?'),

                                                ], id = 'full-plot-header-buttons')
                                    ], id = 'full-plot-details-header'),
                                dbc.Spinner(dbc.Alert('Changes saved successfully.', id = 'plot-save-toast', dismissable=True, is_open=False, duration=5000),spinner_style={"width": "20px", "height": "20px"}, color = 'success'),
                                dbc.Spinner(dbc.Alert('File Processed. Starting Download...', id = 'plot-dwn-toast', dismissable=True, is_open=False, duration=5000),spinner_style={"width": "20px", "height": "20px"}, color = 'info'),
                                html.Div(datatable_content, id = 'full-plot-details-datatable'),

                            ]
            return html.Div(plot_ds_comps, id = 'plot-full-dataset-container')
        else:
            admin_content = html.Div([
                            html.Img(src = access_denied_logo, id = 'admin-not-logged-in-div-img'),
                            html.P('You are not logged in. Please log in to continue.', 'admin-not-logged-in-div-msg')
                        ], id = 'admin-not-logged-in-div')
            return admin_content

    elif(url == '/parkdata'):
        style_table = {'height': '90vh', 'width': '94vw'}
        style_header={'backgroundColor': '#2c3e50',
                      'fontWeight': 'bold',
                      'font-family':'sans-serif',
                      'font-size': 'small',
                      'color': 'white'}

        style_cell={'height': 'auto',
                    'minWidth': '180px',
                    'width': '180px',
                    'maxWidth': '180px',
                    'whiteSpace': 'normal',
                    'textAlign': 'left',
                    'font-family':'sans-serif',
                    'font-size': 'small'}

        style_data_conditional=[{'if': {'row_index': 'odd'},'backgroundColor': 'rgb(248, 248, 248)'},
                                {"if": {"state": "selected"}, "backgroundColor": "#D4F1F4", "border": "1px solid black"},
                                {'if': {'column_id': 'Property'},"backgroundColor": "#2c3e50", 'fontWeight': 'bold',
                                                                'font-family':'sans-serif', 'font-size': 'small', 'color': 'white'}]
        if(is_logged_in):
            park_df = pd.read_excel(park_details_file_path, engine = 'openpyxl')

            datatable_content = dbc.Spinner(dash_table.DataTable(id = 'park-table',
                                      columns = [{'name': i, 'id': i} for i in park_df.columns],
                                      data = park_df.to_dict('records'),
                                      style_table= style_table,
                                      page_size = 20,
                                      fixed_rows = {'headers': True},
                                      style_header=style_header,
                                      style_cell= style_cell,
                                      style_data_conditional=style_data_conditional,
                                      editable=True, sort_action='native', filter_action='native'))

            plot_ds_comps = [html.Div([
                                        html.P('Park Details', id = 'full-park-details-header-text'),
                                        html.Div([
                                                    dbc.Button(html.I(className = 'fas fa-download'), id = 'full-park-download'),
                                                    dbc.Button(html.I(className = 'fas fa-save'), id = 'full-park-save'),
                                                    dbc.Tooltip('Export as Excel File', target = 'full-park-download', placement = 'bottom'),
                                                    dbc.Tooltip('Save Changes', target = 'full-park-save', placement = 'bottom'),
                                                    dcc.Download(id="download-full-park-dataset"),
                                                    dcc.ConfirmDialog(id='full-park-confirm-save-changes',message='Save the changes to the dataset?'),

                                                ], id = 'full-park-header-buttons')
                                    ], id = 'full-park-details-header'),
                                dbc.Spinner(dbc.Alert('Changes saved successfully.', id = 'park-save-toast', dismissable=True, is_open = False, duration=5000),spinner_style={"width": "20px", "height": "20px"}, color = 'success'),
                                html.Div(datatable_content, id = 'full-park-details-datatable'),

                            ]
            return html.Div(plot_ds_comps, id = 'park-full-dataset-container')
        else:
            admin_content = html.Div([
                            html.Img(src = access_denied_logo, id = 'admin-not-logged-in-div-img'),
                            html.P('You are not logged in. Please log in to continue.', 'admin-not-logged-in-div-msg')
                        ], id = 'admin-not-logged-in-div')
            return admin_content


    elif(url == '/login'):
        captcha = generate_captcha()
        plot_ds_comps = [html.Div([
                                    html.P('Login', id = 'full-park-details-header-text')
                                ], id = 'login-header'),
                         dbc.Spinner(dbc.Alert('Login Successful!', id = 'login-message', dismissable=True, fade = True, is_open = False, duration=5000), type = 'grow', color = 'danger'),
                         dbc.Input(id = 'login-username', placeholder = 'Username'),
                         dbc.Input(id = 'login-password', placeholder = 'Password', type = 'password'),
                         html.Img(src = r'data:image/png;base64,{}'.format(captcha[0]), id = 'captcha-image'),
                         html.P(captcha[1], id = 'captcha-text'),
                         dbc.Input(id = 'login-captcha', placeholder = 'Type text shown in image...'),
                         dbc.Button('Login', id = 'login-button'),

                        ]
        return html.Div(plot_ds_comps, id = 'login-container')

    elif(url == '/logout'):
        plot_ds_comps = [html.Div([
                                    html.P('Logout', id = 'full-park-details-header-text')
                                ], id = 'logout-header'),
                         html.P('Proceed to Logout? After logging out, you will be able to access the application in guest mode.', id = 'logout-text'),
                         dbc.Button('Proceed', id = 'logout-proceed'),
                         dbc.Modal([
                                    dbc.ModalBody("You have been logged out successfully."),
                                    dbc.ModalFooter(
                                            dcc.Link(dbc.Button("Okay", id="close", className="ml-auto", color = 'primary'), href = '/', refresh = True)
                                        ),
                                 ], id = 'logout-modal', is_open = False)
                        ]
        return html.Div(plot_ds_comps, id = 'logout-container')

    elif(url == '/log'):
        if(is_logged_in):
            with open(os.path.join(root_dir, 'support_files', 'support.k'), 'rb') as kf:
                key = kf.read()
            user_list_df = decrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)
            user_dd_list = [{'value': x, 'label': x} for x in user_list_df['username'].values]
            plot_ds_comps = [
                            html.Div([
                                        html.Div([
                                                    html.P('Show log for date: ', className = 'log-labels'),
                                                    dcc.DatePickerSingle(id = 'log-date', date = datetime.now(), placeholder = 'Show log for date', display_format = 'DD/MM/YYYY'),
                                                    html.P('Track specific User(s): ', className = 'log-labels', style = {'margin-top': '15px'}),
                                                    dcc.Dropdown(id = 'log-user', options = user_dd_list, multi = True),
                                                    dbc.Button('Show Logs', id = 'log-show-log', color = 'primary')
                                                ], id = 'log-content-sidebar'),
                                        dbc.Spinner(html.Div(html.Div([
                                                    dbc.Alert([html.I(className = 'fas fa-info-circle', style = {'margin-right': '10px'}), 'Select any date to show logs recorded on the given date.'], color = 'info'),


                                                ], id = 'log-content-list'), id = 'log-content-list-main'), color = 'success')
                                    ], id = 'log-content')


                            ]
            return html.Div(plot_ds_comps, id = 'log-container')
        else:
            return dbc.Alert('In order to access the logs, you need to be logged in.', color = 'danger')

    elif(url == '/about'):

        plot_ds_comps = [html.Div([
                                    html.P('About the Project', id = 'about-header-text')
                                ], id = 'about-header'),
                        html.Div([
                                html.P('Bihar Industrial Area Development Authority', id = 'about-content-header'),
                                html.Div([
                                            html.A(html.Img(src = rbs_logo, className = 'about-logo'), href = 'http://www.rbasedservices.com/'),
                                            html.A(html.Img(src = giz_logo, className = 'about-logo'), href = 'https://www.giz.de/en/worldwide/368.html'),
                                            html.A(html.Img(src = siidcul_logo, className = 'about-logo'), href = 'https://www.biadabihar.in/')
                                         ], id = 'about-logos'),
                                html.Div([
                                            html.Div('About Project', className = 'about-cards-header'),
                                            html.Div(dcc.Markdown(about_project), className = 'about-cards-text'),
                                        ], className = 'about-cards'),
                                html.Div([
                                            html.Div('About Bihar Industrial Area Development Authority (BIADA)', className = 'about-cards-header'),
                                            html.Div(dcc.Markdown(about_biada), className = 'about-cards-text'),
                                        ], className = 'about-cards'),
                                html.Div([
                                            html.Div('About Deutsche Gesellschaft fÃ¼r Internationale Zusammenarbeit - India (GIZ)', className = 'about-cards-header'),
                                            html.Div(dcc.Markdown(about_giz), className = 'about-cards-text'),
                                        ], className = 'about-cards'),
                                html.Div([
                                            html.Div('About R Based Services Pvt. Ltd. (RBS)', className = 'about-cards-header'),
                                            html.Div(dcc.Markdown(about_rbs), className = 'about-cards-text'),
                                        ], className = 'about-cards')
                            ], id = 'about-content')]

        return html.Div(plot_ds_comps, id = 'about-container')

    elif(url == '/user'):

        style_table = {'height': '90vh', 'width': '94vw'}
        style_header={'backgroundColor': '#2c3e50',
                      'fontWeight': 'bold',
                      'font-family':'sans-serif',
                      'font-size': 'small',
                      'color': 'white'}

        style_cell={'height': 'auto',
                    'minWidth': '180px',
                    'width': '180px',
                    'maxWidth': '180px',
                    'whiteSpace': 'normal',
                    'textAlign': 'left',
                    'font-family':'sans-serif',
                    'font-size': 'small'}

        style_data_conditional=[{'if': {'row_index': 'odd'},'backgroundColor': 'rgb(248, 248, 248)'},
                                {"if": {"state": "selected"}, "backgroundColor": "#D4F1F4", "border": "1px solid black"},
                                {'if': {'column_id': 'Property'},"backgroundColor": "#2c3e50", 'fontWeight': 'bold',
                                                                'font-family':'sans-serif', 'font-size': 'small', 'color': 'white'}]

        if(is_logged_in):
            style_table = {'height': '80vh', 'width': '50vw'}
            style_header={'backgroundColor': '#303030',
                          'fontWeight': 'bold',
                          'font-family':'sans-serif',
                          'font-size': 'small',
                          'color': 'white'}

            style_cell={'height': 'auto',
                        'minWidth': '100px',
                        'width': '100px',
                        'maxWidth': '100px',
                        'whiteSpace': 'normal',
                        'textAlign': 'left',
                        'font-family':'sans-serif',
                        'font-size': 'small'}

            with open(os.path.join(root_dir, 'support_files', 'support.k'), 'rb') as kf:
                key = kf.read()

            user_df = decrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)
            for c in user_df.columns:
                if(c[:6] == 'Unname'):
                    user_df = user_df.drop(c, axis = 1)
            uname = sin['Username']

            mini_df = user_df[user_df['username'] == uname]
            mini_df = mini_df[mini_df.columns[2:]]

            mini_df_2_show = pd.DataFrame({'Property': mini_df.columns, 'Value': [mini_df[c].values[0] for c in mini_df.columns]})

            datatable_content = dbc.Spinner(dash_table.DataTable(id = 'user-table',
                                      columns = [{'name': i, 'id': i} for i in mini_df_2_show.columns],
                                      data = mini_df_2_show.to_dict('records'),
                                      style_table= style_table,
                                      fixed_rows = {'headers': True},
                                      style_header=style_header,
                                      style_cell= style_cell,
                                      style_data_conditional=style_data_conditional,
                                      editable=True, sort_action='native', filter_action='native'))

            plot_ds_comps = [html.Div([
                                        html.P('User Information', id = 'user-header-text'),
                                        dbc.Button(html.I(className = 'fas fa-save'), id = 'user-save'),
                                        dbc.Tooltip('Save Changes', target = 'user-save', placement = 'bottom'),
                                        dcc.ConfirmDialog(id='user-confirm-save-changes',message='Save changes?'),
                                    ], id = 'user-header'),
                                dbc.Spinner(dbc.Alert('Changes saved successfully.', id = 'user-save-toast', dismissable=True, is_open=False, duration=5000),spinner_style={"width": "20px", "height": "20px"}, color = 'success'),
                                html.Div(datatable_content, id = 'user-details-datatable')
                            ]
            return html.Div(plot_ds_comps, id = 'user-container')
        else:
            admin_content = html.Div([
                            html.Img(src = access_denied_logo, id = 'admin-not-logged-in-div-img'),
                            html.P('You are not logged in. Please log in to continue.', 'admin-not-logged-in-div-msg')
                        ], id = 'admin-not-logged-in-div')
            return admin_content




    else:
        return html.P('Page Under Construction', id = 'page-under-construction')


#============================C A L L B A C K S===========================================================================================
#-------------Callbacks for Main Basic Web Map Page---------------------------------------------------
#Callback to generate options in the park selector Dropdown
@app.callback(Output('park-selector', 'options'), [Input('district-dropdown', 'value')], prevent_initial_call=True)
def generate_park_list(dist):
    global search_df
    mini_df = search_df[search_df['District'] == dist]
    return [{'label': x, 'value': x} for x in mini_df['Name of Industrial Estate'].unique()]


#Callback to generate sector list when park is selected
@app.callback(Output('sector-selector', 'options'), [Input('park-selector', 'value')], prevent_initial_call = True)
def generate_sector_list(park):
    global search_df
    mini_df = search_df[search_df['Name of Industrial Estate'] == park]

    return [{'label': x, 'value': x} for x in mini_df['Sector'].unique()]

#Callback to generate plot list when sector is selected
@app.callback(Output('home-industry-dropdown', 'options'), [Input('sector-selector', 'value'), Input('park-selector', 'value')], prevent_initial_call = True)
def generate_plots_list(sector, park):
    global search_df
    mini_df = search_df[(search_df['Name of Industrial Estate'] == park) & (search_df['Sector'] == sector)]
    print (mini_df)
    return [{'label': x, 'value': y} for x,y in zip(mini_df['Plot Number'], mini_df['UID'])]

#Callback to toggle advanced Query
@app.callback(Output('query-overlay', 'style'), [Input('query-toggle', 'n_clicks')])
def toggle_adv_query(n):
    if(n):
        if(n%2 == 0):
            return {'display': 'none'}
        else:
            return {'display': 'flex'}
    else:
        return {'display': 'none'}

#Callback to show park accroding to the value of park Dropdown
@app.callback(Output('basic-leaflet-main-map', 'viewport'),
              [Input({'type': 'plot', 'index': ALL}, 'n_clicks'), Input('home-industry-dropdown', 'value'), Input('park-selector', 'value')], prevent_initial_call=True)
def go_to_park(a, uidsel, park):
    if(dash.callback_context.triggered[0]['prop_id'] == 'home-industry-dropdown.value'):
        print (dash.callback_context.triggered[0]['prop_id'])
        print (uidsel)
        uid = uidsel
        for f in plot_json['features']:
            if(f['properties']['UID'] == uid):
                centroid_pos = centroid(f['geometry'])['coordinates']
        return {'center': [centroid_pos[1], centroid_pos[0]], 'zoom': 16}
    elif(dash.callback_context.triggered[0]['prop_id'] == 'park-selector.value'):
        park_details_df = pd.read_excel(park_details_file_path, engine = 'openpyxl')
        mini_df = park_details_df[park_details_df['Industrial Estate Name'] == park]
        return {'center': [mini_df['Latitude'].values[0], mini_df['Longitude'].values[0]], 'zoom': 16}
    else:
        uid = dash.callback_context.triggered[0]['prop_id'].split('"')[3]
        for f in plot_json['features']:
            if(f['properties']['UID'] == uid):
                centroid_pos = centroid(f['geometry'])['coordinates']
        return {'center': [centroid_pos[1], centroid_pos[0]], 'zoom': 16}

#Callback to show park popup
@app.callback(Output('park-modal-header', 'children'), Output('park-modal', 'is_open'), [Input('park-selector', 'value'), Input('close-park-modal', 'n_clicks')], prevent_initial_call = True)
def show_park_modal(p, close):
    initiator = dash.callback_context.triggered[0]['prop_id']
    if(initiator == 'park-selector.value'):
        return html.Div([html.Div(p, id = 'park-modal-header-text'),
                        ], id = 'park-modal-header-container'), True
    else:
        return html.Div([html.Div('Closing...', id = 'park-modal-header-text'),
                        ], id = 'park-modal-header-container'), False

@app.callback(Output('park-modal-body', 'children'), [Input('park-selector', 'value'), Input('park-modal', 'is_open')], prevent_initial_call = True)
def show_park_modal_body(p, is_open):
    if(is_open):
        park_details_df = pd.read_excel(park_details_file_path, engine = 'openpyxl')
        mini_df = park_details_df[park_details_df['Industrial Estate Name'] == p]
        #Categories of details as defined in park_details_category.csv
        park_cat_df = pd.read_csv(os.path.join(root_dir, 'support_files', 'park_details_category.csv'))

        details_list = []

        for pc in park_cat_df.columns:
            small_det_list = [html.Summary(pc, className = 'park-modal-summary')]
            pm_vals = park_cat_df[pc].dropna().values

            pm_vals_available = []
            for pm in pm_vals:
                if(pm in park_details_df.columns):
                    pm_vals_available.append(pm)

            small_det_list.append(vertical_table_from_df(mini_df[pm_vals_available]))
            details_list.append(html.Details(small_det_list, className = 'park-modal-details'))

        return details_list
    else:
        return html.Img(src = loading_image, id = 'loading-image-modal')



#Callback to generate labels layer accroding to the value of park Dropdown
@app.callback(Output('plots_label', 'children'), [Input('park-selector', 'value')], prevent_initial_call=True)
def label_park(park):
    plot_df1 = pd.read_excel(plot_details_path, engine = 'openpyxl')
    label_df = plot_df1[plot_df1['Name of Industrial Estate'] == park]
    plt_no = np.asarray(label_df['Plot Number'])
    lat = np.asarray(label_df['Latitude'])
    lon = np.asarray(label_df['Longitude'])
    markers = []
    i = 1
    for i in range (len(lat)):
        if lat[i]>0 and lon[i]>0:
            m1 = dl.CircleMarker(dl.Tooltip(plt_no[i], direction = 'center', permanent = True, className = 'plotlabel'), 
                         center=[lon[i], lat[i]], id="marker{}".format(i), opacity = 0)
            i = i +1
            markers.append(m1)
        else:
            continue
    return (markers)
        

#Callbck to show the table first, then load info
@app.callback(Output('basic-table-container', 'style'),
              [Input('plot-json', 'click_feature'), Input('basic-table-header-close', 'n_clicks'), Input('home-industry-dropdown', 'value')],
              [Input({'type': 'plot', 'index': ALL}, 'n_clicks')], prevent_initial_call=True)
def show_plot_details_panel(clickData, n, a, s):
    if(dash.callback_context.triggered[0]['prop_id'] == 'basic-table-header-close.n_clicks'):
        return {'display': 'none'}
    else:
        return {'display': 'block'}


selected_uid = ''

@app.callback(Output('basic-table-header-text', 'children'),
              Output('basic-table-content', 'children'),
              Output('selected-plot', 'children'), Output('basic-edit-link', 'href'),
              [Input('plot-json', 'click_feature'), Input('basic-table-header-close', 'n_clicks'), Input('home-industry-dropdown', 'value')],
              [Input({'type': 'plot', 'index': ALL}, 'n_clicks')],
              [State('store-login-uk', 'data'), State('store-logout-uk', 'data')], prevent_initial_call=True)
def show_plot_details(clickData, n, suid, a, sin, sout):
    is_logged_in = authenticate_login(sin, sout)
    if(dash.callback_context.triggered[0]['prop_id'] == 'basic-table-header-close.n_clicks'):
        return '', '', [], '/'
    else:
        if(dash.callback_context.triggered[0]['prop_id'] == 'plot-json.click_feature'):
            uid = clickData['properties']["UID"]
        elif(dash.callback_context.triggered[0]['prop_id'] == 'home-industry-dropdown.value'):
            uid = suid
        else:

            uid = dash.callback_context.triggered[0]['prop_id'].split('"')[3]
        plot_df = pd.read_excel(plot_details_path, engine = 'openpyxl')
        global selected_uid
        selected_uid = uid

        mini_df = plot_df[plot_df['UID'] == uid]

        index_val = mini_df.index[0]

        tab_style = {
            'borderBottom': '1px solid #d6d6d6',
            'padding': '6px',
            'fontWeight': 'bold',
            'font-size': 'small'
        }

        tab_selected_style = {
            'borderTop': '1px solid #d6d6d6',
            'border-radius': '10px 10px 0px 0px',
            'borderBottom': '1px solid #d6d6d6',
            'backgroundColor': '#2596be',
            'color': 'white',
            'padding': '6px',
            'font-size': 'small',
            'fontWeight': 'bold',
        }

        if(is_logged_in):
            table_tab_titles_path = os.path.join(root_dir, 'support_files', 'Categorised_headers.csv')
        else:
            table_tab_titles_path = os.path.join(root_dir, 'support_files', 'Categorised_headers_guest.csv')
        cat_headers_df = pd.read_csv(table_tab_titles_path)
        table_tab_info = [{'header': h, 'columns': cat_headers_df[h].dropna().values} for h in cat_headers_df.columns]
        tabs_component = dcc.Tabs(children = [dcc.Tab(label = x['header'], style=tab_style, selected_style=tab_selected_style,
                                            children = table_from_df(mini_df[x['columns']].dropna(axis = 1))) for x in table_tab_info])

        #JSON for selected plot
        with open(plot_json_path) as f:
            plot_json = json.load(f)

        features_list_for_json = []

        for f in plot_json['features']:
            if(f['properties']['UID'] == uid):
                cur_pos = [[i[1], i[0]] for i in f['geometry']['coordinates'][0]]
                features_list_for_json.append(dl.Polyline(positions = cur_pos, color = '#800080', weight = 5, dashArray="10", pane = "markerPane"))


        return '({}) {}'.format(mini_df['Plot Number'].values[0], mini_df['Name of allootte Unit'].values[0]), tabs_component, features_list_for_json, '/editplot?index={}'.format(index_val)

#Callback to download the details of the selected UID
@app.callback(Output('download-dataframe-xlsx', 'data'), Input('basic-table-header-download', 'n_clicks'), prevent_initial_call=True,)
def export_df_to_excel(n):
    global selected_uid
    plot_df = pd.read_excel(plot_details_path, engine = 'openpyxl')
    mini_df = plot_df[plot_df['UID'] == selected_uid]

    return dcc.send_data_frame(mini_df.to_excel, "{}.xlsx".format(selected_uid), sheet_name="Plot Details", engine = 'openpyxl')

#Callback to show area range when area range is changed
@app.callback(Output('area-range-value-display', 'children'), [Input('area-range-slider', 'value')])
def show_area_range(area_range):
    return 'Selected range : {} - {}'.format(round(area_range[0]/1000000, 2), round(area_range[1]/1000000, 2))

#Callback to show filter results panel first
@app.callback(Output('basic-details-container', 'style'),
              [Input('apply-filter-button', 'n_clicks')],
              [Input('basic-filter-header-close', 'n_clicks')], prevent_initial_call=True)
def filter_results_panel(n, close):
    if(dash.callback_context.triggered[0]['prop_id'] == 'apply-filter-button.n_clicks'):
        return {'display': 'block'}
    else:
        return {'display': 'none'}


#Callback to filter plots and show results
@app.callback(Output('filter-results', 'children'),
              Output('basic-filter-results-content', 'children'),
              [Input('apply-filter-button', 'n_clicks')],
              [State('area-range-slider', 'value'),
               State('plot-status-dropdown', 'value'),
               State('pcb-category-dropdown', 'value'),
               State('plot-parkind-dropdown', 'value'),
               State('plot-type-dropdown', 'value')], prevent_initial_call=True)
def filter_results(n, area, plot_status, pcb_cat, park, plt_type):
    if(dash.callback_context.triggered[0]['prop_id'] == 'apply-filter-button.n_clicks'):
        with open(plot_json_path) as f:
            plot_json = json.load(f)

        plot_df = pd.read_excel(plot_details_path, engine = 'openpyxl')

        #Add filters here
        mini_df = plot_df

        #Park Filter
        if(len(park)>0):
            mini_df = mini_df[mini_df['Name of Industrial Estate'].isin(park)]


        #Area filter
        mini_df = mini_df[(mini_df['Geometric Area (in Sq. Mtr.)'] >= area[0])&(mini_df['Geometric Area (in Sq. Mtr.)'] <= area[1])]

        #Plot Status Filter
        if(len(plot_status)>0):
            mini_df = mini_df[mini_df['Plot Status '].isin(plot_status)]


        if(len(pcb_cat)>0):
            mini_df = mini_df[mini_df['PCB Category'].isin(pcb_cat)]

        if(len(plt_type) > 0):
            mini_df = mini_df[mini_df['Type of Plot'].isin(plt_type)]


        uid_list = mini_df['UID'].values

        global filter_results_global_df
        filter_results_global_df = mini_df

        selected_plots_list = []
        for f in plot_json['features']:
            if(f['properties']['UID'] in uid_list):
                cur_pos = [[i[1], i[0]] for i in f['geometry']['coordinates'][0]]
                selected_plots_list.append(dl.Polyline(positions = cur_pos, color = '#ff0000', weight = 3, dashArray="5", pane = "markerPane"))

        details_panel_contents = []
        for c in mini_df['Name of Industrial Estate'].unique():
            mini_mini_df = mini_df[mini_df['Name of Industrial Estate'] == c]
            obj_to_be_added = [html.P('({}) {}'.format(mini_mini_df['Plot Number'].values[i], mini_mini_df['Name of allootte Unit'].values[i]), id = {'type': 'plot', 'index': mini_mini_df['UID'].values[i]} ,className = 'filtered-details-content-company') for i in range(len(mini_mini_df))]
            obj_to_be_added.append(html.Summary('{} ({})'.format(c, len(mini_mini_df)), className = 'filtered-details-content-industry'))

            details_panel_contents.append(html.Details(obj_to_be_added, className = 'filtered-details-content-main'))

        if(len(details_panel_contents)>0):
            return selected_plots_list, details_panel_contents
        else:
            return selected_plots_list, dbc.Alert('No plots found for the current filter combination.', color = 'warning')
    else:
        return [], 'Filter Results Button Clicked'

#Callback to download the filter results
@app.callback(Output('download-filtered-data-xlsx', 'data'), Input('basic-filter-header-download', 'n_clicks'), prevent_initial_call=True,)
def export_to_excel(n):
    global filter_results_global_df

    return dcc.send_data_frame(filter_results_global_df.to_excel, "filter_results.xlsx", sheet_name="Filter Results", engine = 'openpyxl')
#---------------------------------------------------------------------------------------------------


#=======================Callbacks for Park Details Page=============================================================================
selected_park_df_for_download = pd.DataFrame()
#Callback to show park details on clicked
@app.callback(Output('park-details-panel', 'children'),
              [Input('park-markers', 'click_feature'), Input('park-marker-selector', 'value')],
              [State('store-login-uk', 'data'), State('store-logout-uk', 'data')], prevent_initial_call=True,)
def show_park_details(n, sel, sin, sout):
    is_logged_in = authenticate_login(sin, sout)
    park_details_df = pd.read_excel(park_details_file_path, engine = 'openpyxl')

    initiator = dash.callback_context.triggered[0]['prop_id']

    if(initiator == 'park-marker-selector.value'):
        s = sel.split('_')[2]
    else:
        s = n['properties']['tooltip']
    mini_df = park_details_df[park_details_df['Industrial Estate Name'] == s]
    row_index = park_details_df[park_details_df['Industrial Estate Name'] == s].index[0]
    global selected_park_df_for_download
    selected_park_df_for_download = mini_df

    file_name = s.replace(' ', '_').replace(',', '_').replace('-', '_').replace('(', '_').replace(')', '_')

    if(is_logged_in):
        butt_grp = html.Div([dbc.Button(html.I(className = 'fas fa-file-excel'), color = 'success', id = 'export-park-details-excel'),
                  dcc.Link(dbc.Button(html.I(className = 'fas fa-file-pdf'), color = 'danger', style = {'width': '100%'}), id = 'export-park-details-pdf', href = '/maps/{}.jpg'.format(file_name), refresh = True, target = '_blank'),
                  dcc.Link(dbc.Button(html.I(className = 'fas fa-pencil-alt'), color = 'info', style = {'width': '100%'}), id = 'park-edit-park', href = '/editpark?index={}'.format(row_index), refresh = True, target = '_blank')], id = 'export-buttons-container')
    else:
        butt_grp = html.Div([dbc.Button(html.I(className = 'fas fa-file-excel'), color = 'success', id = 'export-park-details-excel'),
                  dbc.Button(html.I(className = 'fas fa-file-pdf'), color = 'danger', id = 'export-park-details-pdf'),
                  dcc.Link(dbc.Button(html.I(className = 'fas fa-pencil-alt'), color = 'info', style = {'width': '100%'}), id = 'park-edit-park', href = '/editpark?index={}'.format(row_index), refresh = True, target = '_blank')], id = 'export-buttons-container', style = {'display': 'none'})
    content = [dbc.Alert(s, id = 'park-details-parkname', color = 'success'),
                vertical_table_from_df(mini_df),
                butt_grp]

    return content



@app.callback(Output('park-details-content', 'style'), [Input('park-markers', 'click_feature'), Input('park-filter-header-close', 'n_clicks'), Input('park-marker-selector', 'value')], prevent_initial_call=True,)
def show_park_details_panel(n, close, sel):
    if(dash.callback_context.triggered[0]['prop_id'] == 'park-markers.click_feature' or dash.callback_context.triggered[0]['prop_id'] == 'park-marker-selector.value'):
        return {'display': 'block'}
    else:
        return {'display': 'none'}

#Download park data as excel
@app.callback(Output('download-park-data-xlsx', 'data'), [Input('export-park-details-excel', 'n_clicks')], prevent_initial_call=True,)
def export_park_data_to_excel(n):
    global selected_park_df_for_download
    df_to_be_downloaded = pd.DataFrame({'Property': selected_park_df_for_download.columns,
                                        'Value': [selected_park_df_for_download[c].values[0] for c in selected_park_df_for_download.columns]})
    if(n):
        return dcc.send_data_frame(df_to_be_downloaded.to_excel, "park_details.xlsx", sheet_name="Park", engine = 'openpyxl')

#Callback to show park accroding to the value of park Dropdown
@app.callback(Output('park-leaflet-main-map', 'viewport'), [Input('park-marker-selector', 'value')], prevent_initial_call=True)
def go_to_park_in_park_page(loc):
    lat = float(loc.split('_')[0])
    lon = float(loc.split('_')[1])
    return {'center': [lat, lon], 'zoom': 17}

#===================================================================================================================================

#=======================================Callbacks for Admin Page====================================================================
#Callback to get list of the plots in a park
@app.callback(Output('edit-plot-data-div-uid', 'options'), [Input('edit-plot-data-div-dist', 'value')], prevent_initial_call=True)
def get_plots_uid_from_dist(d):
    data_df = pd.read_excel(plot_details_path, engine = 'openpyxl')
    mini_df = data_df[data_df['Name of Industrial Estate'] == d]
    return [{'value': j, 'label': i} for i, j in zip(mini_df['UID'].values, mini_df.index)]

#Callback to generate href for edit plot data button
@app.callback(Output('editplot-link', 'children'), [Input('edit-plot-data-div-uid', 'value')])
def generate_href_for_edit_plot_button(uid):
    return dcc.Link(dbc.Button('Edit', id = 'edit-plot-data-div-button', color = 'success'), href = '/editplot?index={}'.format(uid), refresh = True, target = '_blank')

#Callback to generate href for edit park data button
@app.callback(Output('editpark-link', 'children'), [Input('edit-park-data-div-dist', 'value')])
def generate_href_for_edit_park_button(i):
    return dcc.Link(dbc.Button('Edit', id = 'edit-park-data-div-button', color = 'success'), href = '/editpark?index={}'.format(i), refresh = True, target = '_blank')

#===================================================================================================================================

#=================Callback for Plotdata page========================================================================================
#Callback to download the plot details
@app.callback(Output('download-full-plot-dataset', 'data'), Output('plot-dwn-toast', 'is_open'),  Input('full-plot-download', 'n_clicks'), prevent_initial_call=True,)
def download_full_plot_details_excel(n):
    if(n):
        plot_df = pd.read_excel(plot_details_path, engine = 'openpyxl')
        return dcc.send_data_frame(plot_df.to_excel, "plot_details.xlsx", sheet_name="Plot Details", engine = 'openpyxl'), True

#Callback to show a confirmation dialouge to save the dataset
@app.callback(Output('full-plot-confirm-save-changes', 'displayed'),
              Input('full-plot-save', 'n_clicks'))
def confirm_full_plot_save_changes(n):
    if(n):
        return True

#Export df to plot detials file when the confirmation dialouge confirms it
@app.callback(Output('plot-save-toast', 'is_open'),
              [Input('full-plot-confirm-save-changes', 'submit_n_clicks')],
              [State('table', 'data'), State('table', 'columns'), State('store-login-uk', 'data')])
def update_output_plot(n, rows, columns, sin):
    if(n):
        export_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
        uname = sin['Username']
        log_path = os.path.join(root_dir, 'log', 'log_{}_{}_{}.json'.format(datetime.now().year, datetime.now().month, datetime.now().day))
        addlogentry(log_path, 'Edited Plot Data.', uname, file_edited = 'plot-details', before_df = pd.read_excel(plot_details_path, engine = 'openpyxl'), after_df = export_df, col_to_keep = ['UID', 'Name of allootte Unit'])
        export_df.to_excel(plot_details_path, index = None, engine = 'openpyxl')
        return True

#===================================================================================================================================

#=================Callback for Parkdata page========================================================================================
#Callback to download the park details
@app.callback(Output('download-full-park-dataset', 'data'), Input('full-park-download', 'n_clicks'), prevent_initial_call=True,)
def download_full_park_details_excel(n):
    if(n):
        park_df = pd.read_excel(park_details_file_path, engine = 'openpyxl')
        return dcc.send_data_frame(park_df.to_csv, "park_details.xlsx")

#Callback to show a confirmation dialouge to save the dataset
@app.callback(Output('full-park-confirm-save-changes', 'displayed'),
              Input('full-park-save', 'n_clicks'))
def confirm_full_park_save_changes(n):
    if(n):
        return True

#Export df to park detials file when the confirmation dialouge confirms it
@app.callback(Output('park-save-toast', 'is_open'),
              [Input('full-park-confirm-save-changes', 'submit_n_clicks')],
              [State('park-table', 'data'), State('park-table', 'columns'), State('store-login-uk', 'data')])
def update_output_park(n, rows, columns, sin):
    if(n):
        export_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
        uname = sin['Username']
        log_path = os.path.join(root_dir, 'log', 'log_{}_{}_{}.json'.format(datetime.now().year, datetime.now().month, datetime.now().day))
        addlogentry(log_path, 'Edited Park Data.', uname, file_edited = 'park-details', before_df = export_df, after_df = pd.read_excel(park_details_file_path, engine = 'openpyxl'), col_to_keep = ['Industrial Estate Name'])

        export_df.to_excel(park_details_file_path, index = None, engine = 'openpyxl')
        return True

#===================================================================================================================================

#======================Callback for Edit Park Data page=============================================================================
#Callback to open the confirmation dialouge when save changes button is Clicked
@app.callback(Output('edit-park-confirm-save-changes', 'displayed'),
              Input('edit-park-save', 'n_clicks'))
def confirm_edit_park_save_changes(n):
    if(n):
        return True

#Export df to park detials file when the confirmation dialouge confirms it
@app.callback(Output('edit-park-save-toast', 'is_open'),
              [Input('edit-park-confirm-save-changes', 'submit_n_clicks')],
              [State('edit-park-table', 'data'), State('edit-park-table', 'columns'), State('store-login-uk', 'data')])
def update_output_edit_park(n, rows, columns, sin):
    if(n):
        df = pd.read_excel(park_details_file_path, engine = 'openpyxl')
        export_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
        park_name = rows[1]['Value']

        index_val = df[df['Industrial Estate Name'] == park_name].index[0]

        df.loc[index_val, :] = export_df['Value'].values
        uname = sin['Username']
        log_path = os.path.join(root_dir, 'log', 'log_{}_{}_{}.json'.format(datetime.now().year, datetime.now().month, datetime.now().day))
        addlogentry(log_path, 'Edited Park Data.', uname, file_edited = 'park-details', before_df = df, after_df = pd.read_excel(park_details_file_path, engine = 'openpyxl'), col_to_keep = ['Industrial Estate Name'])

        df.to_excel(park_details_file_path, index = None, engine = 'openpyxl')

        return True
#===================================================================================================================================

#======================Callback for Edit Plot Data page=============================================================================
#Callback to open the confirmation dialouge when save changes button is Clicked
@app.callback(Output('edit-plot-confirm-save-changes', 'displayed'),
              Input('edit-plot-save', 'n_clicks'))
def confirm_edit_plot_save_changes(n):
    if(n):
        return True

#Export df to park detials file when the confirmation dialouge confirms it
@app.callback(Output('edit-plot-save-toast', 'is_open'),
              [Input('edit-plot-confirm-save-changes', 'submit_n_clicks')],
              [State('edit-plot-table', 'data'), State('edit-plot-table', 'columns'), State('store-login-uk', 'data')])
def update_output_edit_plot(n, rows, columns, sin):
    if(n):
        df = pd.read_excel(plot_details_path, engine = 'openpyxl')
        export_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
        uid = rows[0]['Value']

        index_val = df[df['UID'] == uid].index[0]

        df.loc[index_val, :] = export_df['Value'].values
        uname = sin['Username']
        log_path = os.path.join(root_dir, 'log', 'log_{}_{}_{}.json'.format(datetime.now().year, datetime.now().month, datetime.now().day))
        addlogentry(log_path, 'Edited Plot Data.', uname, file_edited = 'plot-details', before_df = df, after_df = pd.read_excel(plot_details_path, engine = 'openpyxl'), col_to_keep = ['UID', 'Name of allootte Unit'])


        df.to_excel(plot_details_path, index = None, engine = 'openpyxl')

        return True
#===================================================================================================================================

#===========Login Page Callbacks====================================================================================================
#Callback to authenticate Login
@app.callback(Output('login-message', 'children'), Output('login-message', 'color'), Output('login-message', 'is_open'), Output('store-login-uk', 'data'),
             [Input('login-button', 'n_clicks')],[State('login-username', 'value'), State('login-password', 'value'), State('captcha-text', 'children'), State('login-captcha', 'value')], prevent_initial_call=True)
def authenticate(n, username, password, captcha_actual, captcha_entered):
    if n is None:
        raise PreventUpdate
    #global is_logged_in
    #global current_user_info
    with open(os.path.join(root_dir, 'support_files', 'support.k'), 'rb') as kf:
        key = kf.read()

    user_info_df = decrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)

    mini_df = user_info_df[(user_info_df['username'] == username)&(user_info_df['password'] == password)]
    t = datetime.now()

    with open(os.path.join(root_dir, 'user_login_record.json'), 'r') as openfile:
        login_record = json.load(openfile)

    if(username in login_record.keys()):
        if(login_record[username] == 0):
            allow_login = True
        else:
            allow_login = False
    else:
        allow_login = True

    if(len(mini_df) > 0 and captcha_actual == captcha_entered and allow_login):

        is_logged_in = True
        current_user_info = {'username': username, 'First Name': mini_df['First Name'].values[0], 'Last Name': mini_df['Last Name'].values[0]}
        dict_to_return = {'status': 1, 'Username': username, 'Year': t.year, 'Month': t.month, 'Day': t.day, 'Hour': t.hour, 'Minute': t.minute, 'Second': t.second}
        log_path = os.path.join(root_dir, 'log', 'log_{}_{}_{}.json'.format(datetime.now().year, datetime.now().month, datetime.now().day))
        addlogentry(log_path, 'Logged In', username)

        #Add data to user login records
        login_record[username] = 1

        with open(os.path.join(root_dir, 'user_login_record.json'), "w") as outfile:
            json.dump(login_record, outfile)

        return "Login Successful. Welcome {}!".format(username), "success", True, dict_to_return
    else:
        is_logged_in = False
        dict_to_return = {'status': 0, 'Username': '', 'Year': t.year, 'Month': t.month, 'Day': t.day, 'Hour': t.hour, 'Minute': t.minute, 'Second': t.second}
        return "Login Error! The error might be due to invalid username, wrong password, wrong captcha or the user has been logged in somewhere else.", "danger", True, dict_to_return

#===================================================================================================================================

#===========Logout Page Callbacks====================================================================================================
#Callback to show logout modal
@app.callback(Output('logout-modal', 'is_open'),
             [Input('logout-proceed', 'n_clicks')],  [State('store-login-uk', 'data')], prevent_initial_call=True)
def proceed_to_logout(n, sin):
    if n is None:
        raise PreventUpdate
    t = datetime.now()
    log_path = os.path.join(root_dir, 'log', 'log_{}_{}_{}.json'.format(datetime.now().year, datetime.now().month, datetime.now().day))
    addlogentry(log_path, 'Logged Out', sin['Username'])
    return True



#Callback to update the logout cache
@app.callback(Output('store-logout-uk', 'data'),
             [Input('logout-proceed', 'n_clicks')],  [State('store-login-uk', 'data')], prevent_initial_call=True)
def proceed_to_logout_update_cache(n, sin):
    if n is None:
        raise PreventUpdate
    t = datetime.now()
    uname = sin['Username']
    with open(os.path.join(root_dir, 'user_login_record.json'), 'r') as openfile:
        login_record = json.load(openfile)

    login_record[uname] = 0

    with open(os.path.join(root_dir, 'user_login_record.json'), "w") as outfile:
        json.dump(login_record, outfile)

    return {'Year': t.year, 'Month': t.month, 'Day': t.day, 'Hour': t.hour, 'Minute': t.minute, 'Second': t.second}
#===================================================================================================================================

#========================Userinfo Page Callback=====================================================================================
#Callback to open the confirmation dialouge when save changes button is Clicked
@app.callback(Output('user-confirm-save-changes', 'displayed'),
              Input('user-save', 'n_clicks'))
def confirm_user_save_changes(n):
    if(n):
        return True

#Export df to park detials file when the confirmation dialouge confirms it
@app.callback(Output('user-save-toast', 'is_open'),
              [Input('user-confirm-save-changes', 'submit_n_clicks')],
              [State('user-table', 'data'), State('user-table', 'columns'), State('store-login-uk', 'data')])
def update_output_edit_plot(n, rows, columns, sin):
    if(n):
        with open(os.path.join(root_dir, 'support_files', 'support.k'), 'rb') as kf:
            key = kf.read()

        user_df = decrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)
        for c in list(user_df.columns):
            if(c[:5] == 'Unnam'):
                user_df = user_df.drop(c, axis = 1)

        uname = sin['Username']
        mini_df = user_df[user_df['username'] == uname]
        password_val = mini_df['password'].values[0]

        #Get data from datatable
        first_df = pd.DataFrame({'Property': ['username', 'password'], 'Value': [uname, password_val]})
        export_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
        export_df = pd.concat([first_df, export_df])
        vals = export_df['Value'].values
        #Convert it to horizonal arrangement
        export_df_vert = pd.DataFrame()
        for i in range(len(vals)):
            export_df_vert[export_df['Property'].values[i]] = [vals[i]]

        #Get the original dataset and remove the row containing the uid
        user = export_df_vert['username'].values[0]
        mini_index = mini_df.index[0]

        user_df.loc[mini_index, :] = export_df['Value'].values

        user_df.to_excel(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), engine = 'openpyxl', index = None)
        encrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)

        return True
#===================================================================================================================================

#Callback for log page-------------------------------------------------------------------------------------------------------------
@app.callback(Output('log-content-list', 'children'), [Input('log-show-log', 'n_clicks')],
             [State('log-date', 'date'), State('log-user', 'value')], prevent_initial_call = True)
def render_log(n, date, users):
    if(n):
        date_str = date.split('T')[0]
        log_file = 'log_{}_{}_{}.json'.format(date_str.split('-')[0], int(date_str.split('-')[1]), int(date_str.split('-')[2]))
        log_path = os.path.join(root_dir, 'log', log_file)
        return render_logfile(log_path, users)
#----------------------------------------------------------------------------------------------------------------------------------

#-----Add map folder to static files so that they can be downloaded via simple url------------------------------------------------
@app.server.route('/maps/<path:path>')
def serve_static(path):
    #Set root_dir for the app
    if(os.path.exists('/home/siidcul/ukdis')):
        root_dir = '/home/siidcul/ukdis'
    else:
        root_dir = os.getcwd()
    return flask.send_from_directory(
        os.path.join(root_dir, 'maps'), path
    )
#----------------------------------------------------------------------------------------------------------------------------------

#-----------REST API Calls----------------------------------------------------------------------------------------------------------
@app.server.route('/api/createuser', methods=['GET'])
def createuser():
    if 'username' in request.args:
        uname = request.args['username']
    else:
        return {'response': 'data missing'}
    if 'password' in request.args:
        pwd = request.args['password']
    else:
        return {'response': 'data missing'}
    if 'key' in request.args:
        given_key = request.args['key']
    else:
        return {'response': 'data missing'}

    original_key = '0o9gKlVbJ'

    if(given_key != original_key):
        return {'response': 'invalid key'}
    else:
        try:
            with open(os.path.join(root_dir, 'support_files', 'support.k'), 'rb') as kf:
                key = kf.read()
            user_list_df = decrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)
            new_df = {'username': uname, 'password': pwd}
            user_list_df = user_list_df.append(new_df, ignore_index = True)
            #encrypt
            for c in user_list_df.columns:
                if(c[:6] == 'Unname'):
                    user_list_df = user_list_df.drop(c, axis = 1)
            user_list_df.to_excel(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), engine = 'openpyxl')
            encrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)

            log_path = os.path.join(root_dir, 'log', 'log_{}_{}_{}.json'.format(datetime.now().year, datetime.now().month, datetime.now().day))
            addlogentry(log_path, 'Created User {}'.format(uname), 'Superuser')
            results = {'response': 'success'}
        except:
            results = {'response': 'error occured'}
        return jsonify(results)

@app.server.route('/api/showusers', methods=['GET'])
def showuserlist():
    if 'key' in request.args:
        given_key = request.args['key']
    else:
        return {'response': 'data missing'}

    if 'showpass' in request.args:
        showpass = request.args['showpass']
    else:
        showpass = 'false'

    original_key = '0o7gKl5VbJ1'

    if(given_key != original_key):
        return {'response': 'invalid key'}
    else:
        try:
            with open(os.path.join(root_dir, 'support_files', 'support.k'), 'rb') as kf:
                key = kf.read()
            user_list_df = decrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)

            if(showpass == 'true'):
                results = [{'Username': x, 'Name': '{} {}'.format(y,z), 'Password': a} for x,y,z,a in zip(user_list_df['username'].values,user_list_df['First Name'].values,user_list_df['Last Name'].values, user_list_df['password'].values)]
            else:
                results = [{'Username': x} for x in user_list_df['username'].values]
        except:
            results = {'response': 'error occured'}
        return jsonify(results)

@app.server.route('/api/dropuser', methods=['GET'])
def dropuser():
    if 'username' in request.args:
        uname = request.args['username']
    else:
        return {'response': 'data missing'}
    if 'key' in request.args:
        given_key = request.args['key']
    else:
        return {'response': 'data missing'}

    original_key = '0o9gKlVbJ'

    if(given_key != original_key):
        return {'response': 'invalid key'}
    else:
        try:
            with open(os.path.join(root_dir, 'support_files', 'support.k'), 'rb') as kf:
                key = kf.read()
            user_list_df = decrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)

            if(uname in user_list_df['username'].values):
                user_list_df = user_list_df[user_list_df['username'] != uname]
                for c in user_list_df.columns:
                    if(c[:6] == 'Unname'):
                        user_list_df = user_list_df.drop(c, axis = 1)
                user_list_df.to_excel(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), engine = 'openpyxl')
                encrypt(os.path.join(root_dir, 'support_files', 'user_info.xlsx'), key)
                log_path = os.path.join(root_dir, 'log', 'log_{}_{}_{}.json'.format(datetime.now().year, datetime.now().month, datetime.now().day))
                addlogentry(log_path, 'Deleted User {}'.format(uname), 'Superuser')
                results = {'response': 'success'}
            else:
                results = {'response': 'no such user found'}
        except:
            results = {'response': 'error occured'}
        return jsonify(results)
#-----------------------------------------------------------------------------------------------------------------------------------


Talisman(app.server, content_security_policy={
    "script-src": ["'self'"] + app.csp_hashes() + ["*"] + ["'unsafe-eval'"],
}, force_https=False)

#Talisman(app.server, force_https=False)

if __name__ == '__main__':
    app.run_server()
