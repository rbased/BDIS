import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import json
import os
from datetime import datetime

def addlogentry(log_path, text, username, file_edited = None, before_df = None, after_df = None, col_to_keep = [], say = 1):
    #log_path = 'log_{}_{}_{}.json'.format(datetime.now().year, datetime.now().month, datetime.now().day)

    empty_dict = {'date': {'d': datetime.now().day, 'm': datetime.now().month, 'y': datetime.now().year}, 'entries': []}

    #Check if JSON file exists. If not, then create one.
    if(os.path.exists(log_path) == False):
        with open(log_path, 'w') as f:
            f.write(json.dumps(empty_dict, indent = 4))

    #Now read the JSON file and entries
    with open(log_path, 'r') as openfile:
        log_object = json.load(openfile)

    time_dict = {'h': int(datetime.now().hour), 'm': int(datetime.now().minute), 's': int(datetime.now().second)}

    if before_df is None or after_df is None:
        log_object['entries'].append({'time': time_dict, 'user': username, 'text': text, 'dict_present': 0})
    else:
        #Set the format a little
        if(len(after_df) > len(before_df)):
            if(say == -1):
                sayv = 'Removed'
                change_dict = pd.concat([before_df, after_df]).drop_duplicates(keep=False)
            else:
                sayv = 'Added'
                change_dict = pd.concat([after_df,before_df]).drop_duplicates(keep=False)


            change_dict['File'] = ['Edited'] * len(change_dict)
            change_dict = change_dict.astype('str').to_dict()

            log_object['entries'].append({'time': time_dict, 'user': username, 'file': file_edited, 'text': '{} and/or edited row(s) in {}.'.format(sayv, file_edited), 'dict_present': 1, 'changedict': change_dict, 'col_to_keep': list(after_df.columns)})
        elif(len(after_df) < len(before_df)):
            if(say == -1):
                sayv = 'Added'
                change_dict = pd.concat([before_df, after_df]).drop_duplicates(keep=False)
            else:
                sayv = 'Removed'
                change_dict = pd.concat([after_df,before_df]).drop_duplicates(keep=False)

            change_dict['File'] = ['Edited'] * len(change_dict)
            change_dict = change_dict.astype('str').to_dict()

            log_object['entries'].append({'time': time_dict, 'user': username, 'file': file_edited, 'text': '{} and/or edited row(s) in {}.'.format(sayv, file_edited), 'dict_present': 1, 'changedict': change_dict, 'col_to_keep': list(after_df.columns)})

        else:

            change_dict = before_df.compare(after_df, align_axis=0).rename(index={'self': 'Original', 'other': 'Edited'}, level=-1).to_dict()
            df = pd.DataFrame(change_dict)
            index_vals = [x[0] for x in df.index]
            df.reset_index(drop=True, inplace=True)
            df['File'] = ['Original', 'Edited'] * int(len(df) / 2)

            for k in col_to_keep:
                df[k] = [before_df[k].values[x] for x in index_vals]

            col_arr = ['File'] + col_to_keep
            rest_cols = list(df.columns)
            for r in col_arr:
                rest_cols.remove(r)
            for x in rest_cols: col_arr.append(x)
            df = df[col_arr]
            #print(df)
            change_dict = df.fillna(' ').astype('str').to_dict()

            log_object['entries'].append({'time': time_dict, 'user': username, 'file': file_edited, 'text': text, 'dict_present': 1, 'changedict': change_dict, 'col_to_keep': col_to_keep})

    with open(log_path, 'w') as writefile:
        writefile.write(json.dumps(log_object, indent = 4))

def p(a):
    if(a < 10):
        return '0{}'.format(a)
    else:
        return '{}'.format(a)


def dict_to_table(d, col_to_keep):
    #Colors
    keep_color = 'orange'
    original_color = '#f0a190'
    edited_color = '#9ced51'

    df = pd.DataFrame(d)
    cols = list(df.columns)
    o_color_list = []
    e_color_list = []
    for c in cols:
        if(c in col_to_keep):
            o_color_list.append(keep_color)
            e_color_list.append(keep_color)
        else:
            o_color_list.append(original_color)
            e_color_list.append(edited_color)


    table_elements = [html.Tr([html.Th(x, className = 'log-table-h') for x in df.columns])]

    for i in range(len(df)):
        z = df.values[i]
        td_list = []
        for s, sz in enumerate(z):
            if(df['File'].values[i] == 'Original'):
                td_list.append(html.Td(sz, style = {'background': o_color_list[s]}, className = 'log-table-d'))
            else:
                td_list.append(html.Td(sz, style = {'background': e_color_list[s]}, className = 'log-table-d'))
        table_elements.append(html.Tr(td_list, className = 'log-table-r'))

    return html.Div(html.Table(table_elements, className = 'log-table'), className = 'log-table-container')

def render_logfile(logfile, user_filter = [], file_filter = []):
    if(user_filter == []): user_filter = None
    if(os.path.exists(logfile) == True):
        with open(logfile, 'r') as openfile:
            log_object = json.load(openfile)

        features = log_object['entries']

        if(len(features) ==  0):
            return dbc.Alert([html.I(className = 'fas fa-info-circle', style = {'margin-right': '10px'}), 'No log entries found.'], color = 'danger')
        else:
            elements = []
            for f in features:
                if(user_filter is not None):
                    if(f['user'] in user_filter):

                        tstr = '[{}:{}:{}] {} : {}'.format(p(f['time']['h']), p(f['time']['m']), p(f['time']['s']), f['user'], f['text'])
                        if(f['dict_present'] == 0):
                            if(f['text'] == 'Logged In'):
                                elements.append(html.Div(tstr, className = 'log-only-text-login'))
                            elif(f['text'] == 'Logged Out'):
                                elements.append(html.Div(tstr, className = 'log-only-text-logout'))
                            else:
                                elements.append(html.Div(tstr, className = 'log-only-text'))

                        else:
                            f_list = [html.Summary(tstr, className = 'log-summary'),
                                      html.Div(dict_to_table(f['changedict'], f['col_to_keep']))]

                            elements.append(html.Details(f_list, className = 'log-details'))
                else:
                    tstr = '[{}:{}:{}] {} : {}'.format(p(f['time']['h']), p(f['time']['m']), p(f['time']['s']), f['user'], f['text'])
                    if(f['dict_present'] == 0):
                        if(f['text'] == 'Logged In'):
                            elements.append(html.Div(tstr, className = 'log-only-text-login'))
                        elif(f['text'] == 'Logged Out'):
                            elements.append(html.Div(tstr, className = 'log-only-text-logout'))
                        else:
                            elements.append(html.Div(tstr, className = 'log-only-text'))

                    else:
                        f_list = [html.Summary(tstr, className = 'log-summary'),
                                  html.Div(dict_to_table(f['changedict'], f['col_to_keep']))]

                        elements.append(html.Details(f_list, className = 'log-details'))
            if(len(elements)>0):
                return elements
            else:
                return dbc.Alert([html.I(className = 'fas fa-info-circle', style = {'margin-right': '10px'}), 'No log entries found.'], color = 'danger')
    else:
        return dbc.Alert([html.I(className = 'fas fa-info-circle', style = {'margin-right': '10px'}), 'No log entries found.'], color = 'danger')

def to_log_via_pcb(log_path, username, tstr, file_edited, before_df, after_df, coltokeep):
    before_df.reset_index(drop=True, inplace=True)
    after_df.reset_index(drop=True, inplace=True)

    if(before_df.equals(after_df) == False):
        empty_dict = {'date': {'d': datetime.now().day, 'm': datetime.now().month, 'y': datetime.now().year}, 'entries': []}

        #Check if JSON file exists. If not, then create one.
        if(os.path.exists(log_path) == False):
            with open(log_path, 'w') as f:
                f.write(json.dumps(empty_dict, indent = 4))

        #Now read the JSON file and entries
        with open(log_path, 'r') as openfile:
            log_object = json.load(openfile)

        time_dict = {'h': int(datetime.now().hour), 'm': int(datetime.now().minute), 's': int(datetime.now().second)}


        before_df['File'] = ['Original' for x in range(len(before_df))]
        after_df['File'] = ['Edited' for x in range(len(after_df))]
        before_df.reset_index(drop=True, inplace=True)
        after_df.reset_index(drop=True, inplace=True)
        change_dict = pd.concat([before_df, after_df])
        change_dict.reset_index(drop=True, inplace=True)

        change_dict = change_dict.astype('str').to_dict()

        log_object['entries'].append({'time': time_dict, 'user': username, 'file': file_edited, 'text': tstr, 'dict_present': 1, 'changedict': change_dict, 'col_to_keep': coltokeep})

        with open(log_path, 'w') as writefile:
            writefile.write(json.dumps(log_object, indent = 4))
